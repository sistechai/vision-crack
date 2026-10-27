"""Map the on-screen capture guide to image pixels (paper Sec. 2.1.2, Eq. 1-5)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import LABEL_ASPECT, ROI_ALPHA


@dataclass(frozen=True)
class Roi:
    x: int
    y: int
    w: int
    h: int

    @property
    def xyxy(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.w, self.y + self.h


def preview_roi(image_wh: tuple[int, int], screen_wh: tuple[int, int],
                alpha: float = ROI_ALPHA) -> Roi:
    """ROI in image pixels for a guide covering ``alpha`` of the preview width.

    Eq. 1: w = H_img / H_scr * alpha * W_scr
    Eq. 2: h = 3/5 * w
    Eq. 3: x = (W_img - w) / 2
    Eq. 4: y = H_img - 2h
    """
    w_img, h_img = image_wh
    w_scr, h_scr = screen_wh
    w = round(h_img / h_scr * alpha * w_scr)
    h = round(LABEL_ASPECT * w)
    x = math.ceil((w_img - w) / 2)
    y = h_img - 2 * h
    return Roi(x, y, w, h)
