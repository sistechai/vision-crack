"""Measurement chain for the 45-capture robustness sweep (revision experiments).

Ported from the revision notebook with the same parameters so the published numbers
reproduce. Per capture it:

1. finds the red label frame (``label_rect``): in-plane angle + coverage
   = label area / mean label area of the reference (norm) captures;
2. de-rotates a fixed crop around the reference label position and reads the 18
   bars (``label_bar_positions``). KMeans(5) on the widths gives the thickness classes,
   which are decoded and also give a **barcode-derived scale** (mm/px);
3. measures the 5 printed reference bars above the label by column projection
   (``ref_widths_px``, integer edges, or ``ref_widths_subpixel``) and converts them
   with that scale.

``barcode_band`` (valid-row redundancy) reads the bars inside the hand-drawn label bbox.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from .barcode import decode
from .constants import COVERAGE_MIN, ET_GT_MM
from .io import data_dir, read_rgb
from .scale import barcode_scale

FOLDERS = ["norm", "dist", "roll", "pitch", "yaw"]
FOLDER_INFO = {   # folder → (display name, what changes, gate that should catch it)
    "norm": ("Norm", "reference pose", "—"),
    "dist": ("Distance", "camera farther away", "coverage"),
    "roll": ("Roll", "in-plane rotation", "rotation"),
    "pitch": ("Pitch", "out-of-plane tilt (vertical)", "coverage (height)"),
    "yaw": ("Yaw", "out-of-plane tilt (horizontal)", "coverage (width)"),
}
EXPECTED_CODE = "lewb"
ROI_PAD = 0.35


# ---------------------------------------------------------------- data
def load_sweep() -> pd.DataFrame:
    d = data_dir() / "robustness"
    df = pd.read_csv(d / "metadata.csv")
    df["path"] = [d / f / n for f, n in zip(df.folder, df.file)]
    return df


# ---------------------------------------------------------------- label geometry
def find_red_label(rgb):
    """Largest red-frame contour → cv2.minAreaRect, or None."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    red = (cv2.inRange(hsv, (0, 80, 60), (12, 255, 255)) |
           cv2.inRange(hsv, (168, 80, 60), (180, 255, 255)))
    red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cnts, _ = cv2.findContours(red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    return cv2.minAreaRect(c) if cv2.contourArea(c) > 2000 else None


def inplane_deg(rect) -> float:
    a = rect[2] % 90
    return a if a < 45 else a - 90


def label_rect(rgb):
    """(cx, cy, w, h, angle, area) of the red label, or None."""
    r = find_red_label(rgb)
    if r is None:
        return None
    (cx, cy), (w, h), _ = r
    w, h = max(w, h), min(w, h)
    return cx, cy, w, h, inplane_deg(r), w * h


def derotate(rgb):
    r = find_red_label(rgb)
    if r is None:
        return None, None
    a = inplane_deg(r)
    M = cv2.getRotationMatrix2D(r[0], a, 1.0)
    rot = cv2.warpAffine(rgb, M, (rgb.shape[1], rgb.shape[0]), borderValue=(255, 255, 255))
    return rot, a


def crop_fixed(rgb, ref_box, pad=ROI_PAD):
    """Crop the fixed reference ROI (cx, cy, w, h) with padding."""
    cx, cy, w, h = ref_box
    px, py = w * pad, h * pad
    y0, y1 = max(0, int(cy - h / 2 - py)), int(cy + h / 2 + py)
    x0, x1 = max(0, int(cx - w / 2 - px)), int(cx + w / 2 + px)
    return rgb[y0:y1, x0:x1]


# ---------------------------------------------------------------- bars
def _row_bars(row, minw=6):
    bars, x, n = [], 0, len(row)
    while x < n:
        c = 0
        while x < n and row[x] == 0:
            c += 1
            x += 1
        if c > minw:
            bars.append(float(c))
        x += 1
    return bars


def label_bar_positions(rot_rgb):
    """Per-bar median width (px) inside the de-rotated label, or None."""
    r = find_red_label(rot_rgb)
    if r is None:
        return None
    (cx, cy), (w, h), _ = r
    w, h = max(w, h), min(w, h)
    lab = rot_rgb[max(0, int(cy - h / 2)):int(cy + h / 2),
                  max(0, int(cx - w / 2) + 8):int(cx + w / 2) - 8]
    if lab.size == 0:
        return None
    g = cv2.cvtColor(lab, cv2.COLOR_RGB2GRAY)
    _, th = cv2.threshold(cv2.GaussianBlur(g, (3, 3), 1), 0, 255, cv2.THRESH_OTSU)
    minw = max(3, int(w * 0.006))
    rowbars = [_row_bars(th[i], minw) for i in range(th.shape[0])]
    cnt = collections.Counter(len(b) for b in rowbars if len(b) >= 8)
    if not cnt:
        return None
    n_bars = cnt.most_common(1)[0][0]
    rows = [b for b in rowbars if len(b) == n_bars]
    return np.median(np.array(rows, float), axis=0) if len(rows) >= 8 else None


def classes_and_scale(positions):
    """KMeans(5) on bar widths → (class per bar 1..5, scale mm/px, CoV of per-class scale)."""
    km = KMeans(5, random_state=42, n_init=10).fit(positions.reshape(-1, 1))
    order = np.argsort(km.cluster_centers_.ravel())
    rank = {lab: i + 1 for i, lab in enumerate(order)}
    classes = [rank[l] for l in km.labels_]
    scale, cov = barcode_scale(km.cluster_centers_.ravel())
    return classes, scale, cov


def _ref_band(rot_rgb, geom):
    cx, cy, lw, lh = geom
    y0 = max(int(0.10 * rot_rgb.shape[0]), 0)
    y1 = int(cy - lh / 2 - 0.30 * lh)
    x0 = max(int(cx - 1.15 * lw), 0)
    x1 = min(int(cx + 1.15 * lw), rot_rgb.shape[1])
    if y1 - y0 < 80 or x1 - x0 < 20:
        return None, None
    band = rot_rgb[y0:y1, x0:x1]
    g = cv2.cvtColor(band, cv2.COLOR_RGB2GRAY)
    _, th = cv2.threshold(cv2.GaussianBlur(g, (5, 5), 1), 0, 255,
                          cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV)
    col = (th > 0).sum(0).astype(float)
    on = col > 0.15 * band.shape[0]
    runs, x, n = [], 0, len(on)
    while x < n:
        if on[x]:
            s = x
            while x < n and on[x]:
                x += 1
            runs.append((s, x))
        else:
            x += 1
    runs = [(s, e) for s, e in runs if e - s >= 2]
    if len(runs) < 5:
        return None, None
    runs = sorted(sorted(runs, key=lambda r: -col[r[0]:r[1]].sum())[:5])
    return runs, col


def ref_widths_px(rot_rgb, geom):
    """Integer widths (px, ascending) of the 5 printed reference bars, or None."""
    runs, _ = _ref_band(rot_rgb, geom)
    return None if runs is None else np.sort(np.array([e - s for s, e in runs], float))


def ref_widths_subpixel(rot_rgb, geom, level=0.5):
    """Same bars, edges at the 50 %-of-peak crossing of the column profile (sub-pixel)."""
    runs, col = _ref_band(rot_rgb, geom)
    if runs is None:
        return None

    def cross(pos, thr, rising, win=8):
        m = len(col)
        if rising:
            for k in range(max(1, pos - win), min(m, pos + win + 1)):
                if col[k - 1] < thr <= col[k]:
                    return (k - 1) + (thr - col[k - 1]) / (col[k] - col[k - 1])
        else:
            for k in range(min(m - 2, pos + win), max(-1, pos - win - 1), -1):
                if col[k] >= thr > col[k + 1]:
                    return k + (col[k] - thr) / (col[k] - col[k + 1])
        return None

    out = []
    for s, e in runs:
        thr = level * col[s:e].max()
        L, R = cross(s, thr, True), cross(e - 1, thr, False)
        out.append((R - L) if (L is not None and R is not None and R > L) else float(e - s))
    return np.sort(np.array(out, float))


def _label_geom(rot):
    r = find_red_label(rot)
    if r is None:
        return None
    (cx, cy), (w, h), _ = r
    return cx, cy, max(w, h), min(w, h)


# ---------------------------------------------------------------- per capture
@dataclass
class Reference:
    """Reference (norm) label position and area, used as the fixed ROI."""
    box: tuple          # cx, cy, w, h
    area: float


def reference_from_norm(paths) -> Reference:
    rects = [label_rect(read_rgb(p)) for p in paths]
    arr = np.array([r[:4] for r in rects if r is not None])
    box = tuple(arr.mean(0))
    return Reference(box, box[2] * box[3])


def measure(path, ref: Reference, gt=ET_GT_MM) -> dict:
    """One row of results for a sweep capture."""
    gt = np.asarray(gt)
    row = dict(label_found=False, inplane_deg=np.nan, coverage=np.nan, coverage_ok=False,
               decoded="", decode_ok=False, scale=np.nan, scale_cov_pct=np.nan,
               ref_found=False, ref_mm=None, ref_mae=np.nan, ref_mm_sub=None, ref_mae_sub=np.nan)
    img = read_rgb(path)
    rect = label_rect(img)
    if rect is None:
        return row
    row.update(label_found=True, inplane_deg=abs(rect[4]), coverage=rect[5] / ref.area)
    row["coverage_ok"] = bool(row["coverage"] >= COVERAGE_MIN)

    rot_roi, _ = derotate(crop_fixed(img, ref.box))
    pos = label_bar_positions(rot_roi) if rot_roi is not None else None
    if pos is not None:
        classes, scale, cov = classes_and_scale(pos)
        payload, _ = decode(classes)
        row.update(decoded=payload, decode_ok=payload == EXPECTED_CODE,
                   scale=scale, scale_cov_pct=100 * cov)

    rot, _ = derotate(img)
    geom = _label_geom(rot) if rot is not None else None
    if geom is not None and np.isfinite(row["scale"]):
        w = ref_widths_px(rot, geom)
        if w is not None:
            mm = np.sort(w) * row["scale"]
            row.update(ref_found=True, ref_mm=mm, ref_mae=float(np.abs(mm - gt).mean()))
            ws = ref_widths_subpixel(rot, geom)
            if ws is not None:
                mms = np.sort(ws) * row["scale"]
                row.update(ref_mm_sub=mms, ref_mae_sub=float(np.abs(mms - gt).mean()))
    return row


# ---------------------------------------------------------------- valid rows
def _dark_runs(row, minw=6):
    runs, x, n = [], 0, len(row)
    while x < n:
        if row[x] == 0:
            s = x
            while x < n and row[x] == 0:
                x += 1
            if x - s > minw:
                runs.append((s, x))
        else:
            x += 1
    return runs


def barcode_band(crop_rgb) -> dict:
    """Largest contiguous band of rows that resolve every bar (red frame removed).

    Returns n_bars, valid_rows (band height), band (r0, r1), runs and the width matrix M.
    """
    m = crop_rgb.copy()
    hsv = cv2.cvtColor(m, cv2.COLOR_RGB2HSV)
    red = (cv2.inRange(hsv, (0, 70, 50), (14, 255, 255)) |
           cv2.inRange(hsv, (166, 70, 50), (180, 255, 255)))
    m[cv2.dilate(red, np.ones((3, 3), np.uint8)) > 0] = 255
    g = cv2.cvtColor(m, cv2.COLOR_RGB2GRAY)
    _, th = cv2.threshold(cv2.GaussianBlur(g, (3, 3), 1), 0, 255, cv2.THRESH_OTSU)
    runs = [_dark_runs(th[r]) for r in range(th.shape[0])]
    counts = [len(r) for r in runs]
    cnt = collections.Counter(c for c in counts if c >= 8)
    out = dict(n_bars=0, valid_rows=0, band=(0, 0), runs=runs, M=np.empty((0, 0)))
    if not cnt:
        return out
    N = cnt.most_common(1)[0][0]
    best, bl, i, n = (0, 0), 0, 0, len(counts)
    while i < n:
        if counts[i] == N:
            j = i
            while j < n and counts[j] == N:
                j += 1
            if j - i > bl:
                bl, best = j - i, (i, j)
            i = j
        else:
            i += 1
    if bl < 8:
        return out
    M = np.array([[e - s for s, e in runs[k]] for k in range(*best)], float)
    return dict(n_bars=N, valid_rows=bl, band=best, runs=runs, M=M)


def label_crop(rgb, row) -> np.ndarray:
    """Hand-drawn label bbox crop from a metadata row."""
    x, y, w, h = int(row.label_x), int(row.label_y), int(row.label_w), int(row.label_h)
    return rgb[y:y + h, x:x + w]


def kmeans_core(M):
    """KMeans class sequence of the StartC..Stop core, or None."""
    if M.size == 0:
        return None
    pos = np.median(M, 0)
    km = KMeans(5, random_state=42, n_init=10).fit(pos.reshape(-1, 1))
    order = np.argsort(km.cluster_centers_.ravel())
    rank = {l: i + 1 for i, l in enumerate(order)}
    seq = ''.join(str(rank[l]) for l in km.labels_)
    i = seq.find('543')
    j = seq.find('123', i) if i >= 0 else -1
    if i < 0 or j < 0 or (j - i) % 3:
        return None
    return [int(c) for c in seq[i:j + 3]]


def run_all(df: pd.DataFrame | None = None) -> tuple[pd.DataFrame, Reference]:
    """Measure every sweep capture. Returns (results, reference)."""
    df = load_sweep() if df is None else df
    ref = reference_from_norm(df[df.folder == "norm"].path)
    rows = []
    for r in df.itertuples():
        img = read_rgb(r.path)
        res = measure(r.path, ref)
        band = barcode_band(label_crop(img, r))
        res.update(valid_rows=band["valid_rows"], n_bars=band["n_bars"],
                   bpattern_core=kmeans_core(band["M"]))
        rows.append({**r._asdict(), **res})
    out = pd.DataFrame(rows).drop(columns="Index")
    return out, ref
