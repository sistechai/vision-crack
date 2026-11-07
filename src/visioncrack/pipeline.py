"""End-to-end measurement of one capture: barcode crop → ET crop → widths in mm."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import (BARCODE_MARGIN_X, BARCODE_MARGIN_Y_FRAC, ET_BAND_BOTTOM,
                        ET_BAND_TOP, ET_LAYOUT, MIN_RUN_PX, N_BARCODE_BARS)
from .roi import Roi
from .scale import mm_per_px
from .width import binarize, blur_gray, column_means, measurement_matrix


@dataclass
class Measurement:
    widths_px: np.ndarray        # per ET class (ET-1..ET-5), pixels
    widths_mm: np.ndarray        # per ET class, mm
    scale: float                 # mm / px
    barcode_thresh: float        # Otsu threshold found on the barcode crop
    barcode_M: np.ndarray        # measurement matrix of the 18 barcode bars
    et_M: np.ndarray             # measurement matrix of the ET bars (layout order)
    barcode_box: tuple[int, int, int, int]  # x0, y0, x1, y1 in image px
    et_box: tuple[int, int, int, int]


def barcode_box(bbox: np.ndarray, roi: Roi) -> tuple[int, int, int, int]:
    """Barcode crop inside the detected corners (TL, TR, BL, BR, ROI coords)."""
    (tlx, tly), (trx, try_), (blx, bly), (brx, bry) = np.asarray(bbox, int)
    ox, oy = BARCODE_MARGIN_X, int(roi.h * BARCODE_MARGIN_Y_FRAC)
    cw = (trx - tlx + brx - blx) // 2 - 2 * ox
    ch = (bry - try_ + bly - tly) // 2 - 2 * oy
    cx, cy = roi.x + tlx + ox, roi.y + tly + oy
    return int(cx), int(cy), int(cx + cw), int(cy + ch)


def measure_capture(rgb: np.ndarray, bbox: np.ndarray, roi: Roi,
                    layout: tuple[int, ...] = ET_LAYOUT,
                    paper_compat: bool = True, min_run: int = MIN_RUN_PX) -> Measurement:
    """Measure the printed ET bars in one capture, as done for Table 1.

    1. Barcode crop → Otsu. The threshold is reused for the ET crop so both
       crops are binarized under the same lighting.
    2. ET crop: a band ET_BAND_TOP..ET_BAND_BOTTOM px above the barcode crop,
       same horizontal extent.
    3. Matrix M → clipped column mean → reorder by ET class → × scale.
    """
    x0, y0, x1, y1 = barcode_box(bbox, roi)
    t, bin_bc = binarize(blur_gray(rgb[y0:y1, x0:x1], paper_compat))
    barcode_M = measurement_matrix(bin_bc, N_BARCODE_BARS, min_run)

    ex0, ey0, ex1, ey1 = x0, y0 - ET_BAND_TOP, x1, y0 - ET_BAND_BOTTOM
    _, bin_et = binarize(blur_gray(rgb[ey0:ey1, ex0:ex1], paper_compat), thresh=t)
    et_M = measurement_matrix(bin_et, len(layout), min_run)

    mu = column_means(et_M)
    by_class = np.empty(len(layout))
    for col, cls in enumerate(layout):
        by_class[cls - 1] = mu[col]

    s = mm_per_px(roi.w)
    return Measurement(by_class, by_class * s, s, float(t), barcode_M, et_M,
                       (x0, y0, x1, y1), (ex0, ey0, ex1, ey1))
