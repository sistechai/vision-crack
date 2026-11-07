"""Field test: one real wall crack captured repeatedly with the capture app.

The label (printed on clear film) is stuck over the crack. Per photo this module:

1. finds the red frame: in-plane angle, the 4 corners and their edge-length ratios (keystone);
2. reads the barcode from a **row-median profile** of the de-rotated label. The median removes the
   crack, which crosses the label but sits in any one column for only a few rows. Bars are cut at
   half height between ink and paper (sub-pixel), so the bars and the crack use the same edge rule;
3. decodes the 18 bars, then fits the scale (mm/px) to the known class widths of the decoded label;
4. tracks the crack in a fixed band above the label (given in mm, so every photo measures the same
   piece of crack) and measures its width per row, perpendicular to the local crack direction.

Selection of photos uses capture-quality numbers only (steps 1–3), never the crack width.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import KMeans

from .barcode import decode, encode
from .constants import BARCODE_CLASS_MM, LABEL_WIDTH_MM, MIN_RUN_PX, N_BARCODE_BARS
from .io import read_rgb
from .sweep import find_red_label, inplane_deg
from .width import binarize, blur_gray, clipped_mean

BAND_MM = (3.0, 13.0)   # crack band: this far above the red frame's top edge
TRACK_WIN_PX = 45       # half-width of the window used to measure the crack, per row
TRACK_STEP_PX = 6       # the crack centre may move this far between rows before a wider search
MIN_CONTRAST = 20       # grey levels between paper and crack core; weaker rows are skipped
SLOPE_SMOOTH = 15       # rows on each side used to smooth the crack centre line
# Five 2-mm measuring points along the crack (mm above the frame top), laid out like ET-1..ET-5 in Table 1
POINTS_MM = ((3.0, 5.0), (5.0, 7.0), (7.0, 9.0), (9.0, 11.0), (11.0, 13.0))
POINT_NAMES = tuple(f"P{i + 1}" for i in range(len(POINTS_MM)))


# ---------------------------------------------------------------- red frame
def red_mask(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    red = (cv2.inRange(hsv, (0, 80, 60), (12, 255, 255)) |
           cv2.inRange(hsv, (168, 80, 60), (180, 255, 255)))
    return cv2.morphologyEx(red, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))


def frame_corners(rgb: np.ndarray) -> np.ndarray | None:
    """Outer corners of the red frame as TL, TR, BL, BR (image px), or None."""
    cnts, _ = cv2.findContours(red_mask(rgb), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = cv2.convexHull(max(cnts, key=cv2.contourArea))
    p = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True).reshape(-1, 2).astype(float)
    if len(p) != 4:
        return None
    s, d = p.sum(1), p[:, 0] - p[:, 1]
    return np.array([p[s.argmin()], p[d.argmax()], p[d.argmin()], p[s.argmax()]])


def keystone(q: np.ndarray) -> tuple[float, float]:
    """(top/bottom, left/right) edge-length ratios. 1.0 = no perspective tilt."""
    tl, tr, bl, br = q
    n = np.linalg.norm
    return float(n(tr - tl) / n(br - bl)), float(n(bl - tl) / n(br - tr))


def derotate(rgb: np.ndarray, angle: float, centre) -> np.ndarray:
    M = cv2.getRotationMatrix2D(tuple(map(float, centre)), angle, 1.0)
    return cv2.warpAffine(rgb, M, (rgb.shape[1], rgb.shape[0]), flags=cv2.INTER_LINEAR,
                          borderValue=(255, 255, 255))


# ---------------------------------------------------------------- 1-D profile tools
def half_max_runs(profile: np.ndarray, paper: float, ink: float) -> list[tuple[float, float]]:
    """Dark runs of a 1-D grey profile, edges at the half-height level (linear interpolation)."""
    thr = (paper + ink) / 2
    dark = profile < thr
    runs, i, n = [], 0, len(profile)
    while i < n:
        if dark[i]:
            j = i
            while j < n and dark[j]:
                j += 1
            left = i - 1 + (profile[i - 1] - thr) / (profile[i - 1] - profile[i]) if i > 0 else float(i)
            right = (j - 1 + (profile[j - 1] - thr) / (profile[j - 1] - profile[j])) if j < n else float(j - 1)
            runs.append((left, right))
            i = j
        else:
            i += 1
    return runs


def grey(rgb: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(float), (3, 3), 1)


# ---------------------------------------------------------------- barcode → scale
def barcode_profile(g: np.ndarray, box) -> tuple[np.ndarray, int]:
    """Row-median grey profile across the bars, and the x offset of the profile.

    ``box`` is the de-rotated red frame (x0, y0, x1, y1). The bars fill the middle of the label;
    rows 35–75 % of the frame height avoid the title text and the code text.
    """
    x0, y0, x1, y1 = box
    h, w = y1 - y0, x1 - x0
    ys, ye = int(y0 + 0.35 * h), int(y0 + 0.75 * h)
    xs, xe = int(x0 + 0.04 * w), int(x1 - 0.04 * w)
    return np.median(g[ys:ye, xs:xe], axis=0), xs


def read_barcode(g: np.ndarray, box) -> dict:
    prof, xoff = barcode_profile(g, box)
    paper, ink = np.percentile(prof, 95), np.percentile(prof, 2)
    runs = [r for r in half_max_runs(prof, paper, ink) if r[1] - r[0] > 2]
    out = dict(n_bars=len(runs), code="", decode_ok=False, scale=np.nan, scale_resid_pct=np.nan,
               bars_px=np.array([r[1] - r[0] for r in runs]), bar_x=[(a + xoff, b + xoff) for a, b in runs])
    if len(runs) != N_BARCODE_BARS:
        return out
    px = out["bars_px"]
    km = KMeans(5, random_state=42, n_init=10).fit(px.reshape(-1, 1))
    rank = {lab: i + 1 for i, lab in enumerate(np.argsort(km.cluster_centers_.ravel()))}
    code, ok = decode([rank[lab] for lab in km.labels_])
    out.update(code=code, decode_ok=ok)
    if ok:
        # Printed bars are wider than nominal by a constant (ink spread, ~2 px here), so fit
        # px = mm / s + offset and take the scale from the slope only.
        mm = np.asarray(BARCODE_CLASS_MM)[np.asarray(encode(code)) - 1]
        slope, offset = np.polyfit(mm, px, 1)
        resid = px - (slope * mm + offset)
        out.update(scale=float(1 / slope), ink_spread_px=float(offset),
                   scale_resid_pct=float(100 * resid.std() / px.mean()))
    return out


# ---------------------------------------------------------------- crack
def crack_widths(g: np.ndarray, x_lo: int, x_hi: int, y0: int, y1: int,
                 win: int = TRACK_WIN_PX, step: int = TRACK_STEP_PX) -> tuple[np.ndarray, np.ndarray]:
    """Per-row crack width (px, perpendicular to the crack) and centre x, for rows y0..y1.

    Tracking starts next to the label (bottom row, where the crack is sharpest) and moves up.
    Each row looks for the crack within ±step px of the previous centre. Only if the crack is
    too faint there does it search the full ±win window; rows where it stays too faint are NaN
    and keep the previous centre.
    """
    x = int(np.argmin(g[max(y0, y1 - 40):y1, x_lo:x_hi].mean(0))) + x_lo
    n = y1 - y0
    xs, ws = np.empty(n), np.full(n, np.nan)
    for k in range(n - 1, -1, -1):
        r = g[y0 + k, x - win:x + win + 1]
        paper = float(np.median(r))
        i = win - step + int(np.argmin(r[win - step:win + step + 1]))
        if paper - r[i] <= MIN_CONTRAST:
            j = int(np.argmin(r))
            if paper - r[j] > MIN_CONTRAST:
                i = j
        ink = float(r[i])
        if paper - ink > MIN_CONTRAST:
            for a, b in half_max_runs(r, paper, ink):
                if a <= i <= b + 1:
                    ws[k] = b - a
                    break
            x = x - win + i
        xs[k] = x
    k = SLOPE_SMOOTH
    centre = np.convolve(np.pad(xs, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    cos = np.cos(np.arctan(np.gradient(centre)))
    return ws * cos, xs


def paper_rule_widths(rgb_rot: np.ndarray, barcode_box, xs: np.ndarray, y0: int,
                      win: int = TRACK_WIN_PX, min_run: int = MIN_RUN_PX) -> np.ndarray:
    """Per-row crack width (px) with the Table 1 rule (Sec. 2.3.1), for rows y0..y0+len(xs).

    Blur 3×3 σ=2 → binarize with the Otsu threshold of the barcode crop (as for the ET bars) →
    the dark run (> 6 px) that holds the tracked crack centre. Horizontal width, no direction
    correction (the paper's bars are vertical). NaN where no such run exists.
    ``min_run=0`` keeps every run, to show what the 6-px filter removes.
    """
    bx0, by0, bx1, by1 = barcode_box
    t, _ = binarize(blur_gray(rgb_rot[by0:by1, bx0:bx1]))
    out = np.full(len(xs), np.nan)
    for k, xc in enumerate(xs.astype(int)):
        y = y0 + k
        x_lo = xc - win
        # blur a few rows around y so the 3×3 kernel sees real neighbours
        strip = blur_gray(rgb_rot[y - 2:y + 3, x_lo:xc + win + 1])[2]
        _, line = binarize(strip, thresh=t)
        line = line.ravel()
        i, n = 0, len(line)
        while i < n:
            if line[i] == 0:
                j = i
                while j < n and line[j] == 0:
                    j += 1
                if j - i > min_run and i <= win <= j:
                    out[k] = j - i
                    break
                i = j
            else:
                i += 1
    return out


def middle_row(v: np.ndarray, y_mm: np.ndarray) -> float:
    """Width of the row in the middle of a piece by position (row 17 of 34, counted up from the label)."""
    order = np.argsort(y_mm)
    return float(v[order][(len(v) - 1) // 2])


def point_values(r: "FieldResult", rule: str = "subpixel", scale: str = "barcode",
                 points=POINTS_MM, stat: str = "median", min_run: int = MIN_RUN_PX) -> np.ndarray:
    """Width (mm) of each 2-mm piece of the crack for one photo.

    rule  : ``subpixel`` = half-height widths; ``paper`` = Table 1 rule widths (Otsu of the barcode, runs > 6 px).
    scale : ``barcode`` (fitted to the decoded bars) or ``label`` (50 mm / frame width, Eq. 10).
    stat  : ``median`` of the rows; ``mean`` of the rows; ``middle`` = the one row in the middle of the piece;
            ``clipped`` = mean after dropping rows outside mean ± 1.645 σ (paper Eq. 9, used for the Table 1 rule).
    min_run : Table 1 rule only; a row counts if its dark run is longer than this (paper: 6 px).
    """
    s = r.scale if scale == "barcode" else LABEL_WIDTH_MM / r.frame_w_px
    if rule == "subpixel":
        rows = r.rows_mm / r.scale
    else:   # Table 1 rule: keep dark runs longer than min_run px (paper: 6)
        rows = np.where(r.rows_px_paper_all > min_run, r.rows_px_paper_all, np.nan)
    out = []
    for lo, hi in points:
        m = (r.rows_y_mm >= lo) & (r.rows_y_mm < hi)
        v, y = rows[m], r.rows_y_mm[m]
        if stat == "middle":
            out.append(middle_row(v, y) * s)
            continue
        v = v[np.isfinite(v)]
        if v.size == 0:
            out.append(np.nan)
        elif stat == "median":
            out.append(float(np.median(v)) * s)
        elif stat == "mean":
            out.append(float(v.mean()) * s)
        else:
            out.append(clipped_mean(v) * s)
    return np.array(out)


# ---------------------------------------------------------------- one photo
@dataclass
class FieldResult:
    file: str
    label_found: bool = False
    angle_deg: float = np.nan
    frame_w_px: float = np.nan
    frame_h_px: float = np.nan
    tb_ratio: float = np.nan
    lr_ratio: float = np.nan
    sharpness: float = np.nan
    n_bars: int = 0
    code: str = ""
    decode_ok: bool = False
    scale: float = np.nan
    scale_resid_pct: float = np.nan
    ink_spread_px: float = np.nan
    frame_w_mm: float = np.nan
    top_mm: float = np.nan           # height of the image above the frame top, mm
    crack_px: float = np.nan
    crack_mm: float = np.nan
    crack_mm_label: float = np.nan   # same crack, label-width scale 50 mm / frame width (paper Eq. 10)
    crack_row_sd_mm: float = np.nan
    valid_rows: float = np.nan
    rows_mm: np.ndarray = field(default=None, repr=False)     # per-row width, mm
    rows_y_mm: np.ndarray = field(default=None, repr=False)   # row height above the frame top, mm
    rows_px_paper: np.ndarray = field(default=None, repr=False)  # per-row width, Table 1 rule (> 6 px), px
    rows_px_paper_all: np.ndarray = field(default=None, repr=False)  # same, every dark run (no length filter)


def measure_field(path: str | Path, band_mm=BAND_MM) -> FieldResult:
    res = FieldResult(Path(path).name)
    rgb = read_rgb(path)
    rect = find_red_label(rgb)
    q = frame_corners(rgb)
    if rect is None or q is None:
        return res
    (cx, cy), (w, h), _ = rect
    res.label_found = True
    res.angle_deg = inplane_deg(rect)
    res.frame_w_px, res.frame_h_px = max(w, h), min(w, h)
    res.tb_ratio, res.lr_ratio = keystone(q)
    x0, y0 = q.min(0).astype(int)
    x1, y1 = q.max(0).astype(int)
    res.sharpness = float(cv2.Laplacian(cv2.cvtColor(rgb[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY),
                                        cv2.CV_64F).var())

    rot = derotate(rgb, res.angle_deg, (cx, cy))
    g = grey(rot)
    box = (int(cx - res.frame_w_px / 2), int(cy - res.frame_h_px / 2),
           int(cx + res.frame_w_px / 2), int(cy + res.frame_h_px / 2))
    bc = read_barcode(g, box)
    res.n_bars, res.code, res.decode_ok = bc["n_bars"], bc["code"], bc["decode_ok"]
    res.scale, res.scale_resid_pct = bc["scale"], bc["scale_resid_pct"]
    res.ink_spread_px = bc.get("ink_spread_px", np.nan)
    if not np.isfinite(res.scale):
        return res
    res.frame_w_mm = res.frame_w_px * res.scale
    res.top_mm = box[1] * res.scale

    top = box[1]
    cy0, cy1 = int(top - band_mm[1] / res.scale), int(top - band_mm[0] / res.scale)
    ws, xs = crack_widths(g, box[0], box[2], cy0, cy1)
    h, w = box[3] - box[1], box[2] - box[0]
    bc_box = (int(box[0] + 0.04 * w), int(box[1] + 0.35 * h), int(box[2] - 0.04 * w), int(box[1] + 0.75 * h))
    res.rows_px_paper_all = paper_rule_widths(rot, bc_box, xs, cy0, min_run=0)
    res.rows_px_paper = np.where(res.rows_px_paper_all > MIN_RUN_PX, res.rows_px_paper_all, np.nan)
    mm = ws * res.scale
    res.rows_mm = mm
    res.valid_rows = float(np.isfinite(mm).mean())
    res.crack_px = float(np.nanmedian(ws))
    res.crack_mm = float(np.nanmedian(mm))
    res.crack_mm_label = res.crack_px * LABEL_WIDTH_MM / res.frame_w_px
    res.rows_y_mm = (top - np.arange(cy0, cy1)) * res.scale
    res.crack_row_sd_mm = float(np.nanstd(mm))
    return res
