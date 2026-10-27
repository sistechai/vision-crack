"""Pixel → millimetre scale (paper Sec. 2.3.2, Eq. 10).

Two definitions are used in this repository. Which one applies matters when reading the numbers:

**Label-width scale** (``mm_per_px``, Table 1). The paper's Eq. 10, s = 50 mm / w_ROI.
In the Table 1 pipeline, w_ROI is the **preview-guide ROI width** in image pixels (797 px).
That is not a width detected per image. It works because the capture gates force the label to fill
> 95 % of that ROI, so ROI width ≈ label width in every accepted frame.

**Barcode-class scale** (``barcode_scale``, robustness sweep). The 18 bars are clustered into their 5
thickness classes (0.5–2.5 mm). The scale is the mean of class_mm / class_px. It is measured per capture, so it
follows the camera distance. It also avoids one issue found in the revision work: the red frame of label
"#1" spans ≈ 44 mm rather than 50 mm, which makes 50 mm / frame width overshoot by ≈ 13 %.
"""

from __future__ import annotations

import numpy as np

from .constants import BARCODE_CLASS_MM, LABEL_WIDTH_MM


def mm_per_px(roi_width_px: float, label_mm: float = LABEL_WIDTH_MM) -> float:
    """Label-width scale, s = 50 mm / w_ROI (Eq. 10)."""
    return label_mm / roi_width_px


def barcode_scale(class_centres_px) -> tuple[float, float]:
    """Barcode-class scale from the 5 class centre widths (px, any order).

    Returns (scale mm/px, coefficient of variation of the per-class scales).
    """
    per_class = np.asarray(BARCODE_CLASS_MM) / np.sort(np.asarray(class_centres_px, float))
    return float(per_class.mean()), float(per_class.std() / per_class.mean())
