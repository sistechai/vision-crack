"""Capture-condition gates (paper Sec. 2.2, Steps 2-4). Same logic as the mobile app."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .constants import COVERAGE_MIN, ROTATION_MAX_DEG


@dataclass
class GateResult:
    corners_found: bool                         # Step 2
    coverage_ok: bool = False                   # Step 3
    rotation_ok: bool = False                   # Step 4
    ratios: dict = field(default_factory=dict)  # top / right / bottom / left side ÷ ROI side
    angle_deg: float = float("nan")             # |90° − θ|, signed

    @property
    def accepted(self) -> bool:
        return self.corners_found and self.coverage_ok and self.rotation_ok

    @property
    def first_failure(self) -> str:
        if not self.corners_found:
            return "corners"
        if not self.coverage_ok:
            return "coverage"
        if not self.rotation_ok:
            return "rotation"
        return ""


def evaluate(corners, roi_w: float, roi_h: float,
             coverage_min: float = COVERAGE_MIN,
             rotation_max_deg: float = ROTATION_MAX_DEG) -> GateResult:
    """Run Steps 2-4 on corners given as TL, TR, BL, BR (4×2, ROI coordinates) or None.

    Step 3 (Eq. 6-7): d_top = |x2-x1|, d_right = |y4-y2|, d_bottom = |x4-x3|,
    d_left = |y3-y1|; each must exceed ``coverage_min`` of the ROI side.
    Step 4 (Eq. 8-9): θ from TL→BL, accepted if |90° − θ| < ``rotation_max_deg``.
    All three gates are always computed so failures can be reported; ``accepted``
    applies them in order, as the app does.
    """
    if corners is None:
        return GateResult(False)
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = np.asarray(corners, float)
    ratios = {
        "top": abs(x2 - x1) / roi_w,
        "right": abs(y4 - y2) / roi_h,
        "bottom": abs(x4 - x3) / roi_w,
        "left": abs(y3 - y1) / roi_h,
    }
    angle = 90.0 - math.degrees(math.atan2(y3 - y1, x3 - x1))
    return GateResult(
        corners_found=True,
        coverage_ok=all(r > coverage_min for r in ratios.values()),
        rotation_ok=abs(angle) < rotation_max_deg,
        ratios=ratios,
        angle_deg=angle,
    )
