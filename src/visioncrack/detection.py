"""Barcode corner detection, a port of the mobile app (paper Sec. 2.2, Step 1).

Mirrors ``mobile/.../detection.dart`` (``quantizeUsingHSV``, ``findRedBlocksInRegion``,
``getTop/BottomBoundaryBlocks``) so the Python and phone results can be compared.

1. Colour-quantize the ROI to red / white / black in HSV (OpenCV scale).
2. Slide a 2x2 window; a block is red if at least 3 of its 4 pixels are red.
3. In a band at the top and at the bottom of the ROI, the red block closest to
   each ROI corner is taken as that corner of the label.

The app searches **64-px bands** at the top and bottom, not the full halves the
manuscript describes; the port keeps the app's behaviour (``band=64``).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

RED_HUE = ((0, 10), (160, 180))
RED_MIN_SV = 100
WHITE_MAX_S, WHITE_MIN_V = 50, 200
BLACK_MAX_V = 50
BLOCK = 2
BAND_PX = 64
MAX_BLOCKS = 15000             # the app treats a band with more red blocks than this as noise


def quantize(rgb: np.ndarray) -> np.ndarray:
    """Return a label image: 0 = white, 1 = red, 2 = black (anything else → white)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red_h = ((h >= RED_HUE[0][0]) & (h <= RED_HUE[0][1])) | ((h >= RED_HUE[1][0]) & (h <= RED_HUE[1][1]))
    red = red_h & (s >= RED_MIN_SV) & (v >= RED_MIN_SV)
    white = (s <= WHITE_MAX_S) & (v >= WHITE_MIN_V)
    black = v <= BLACK_MAX_V
    out = np.zeros(h.shape, np.uint8)
    out[black & ~white & ~red] = 2
    out[red] = 1
    return out


def quantized_rgb(labels: np.ndarray) -> np.ndarray:
    """Colour image of a ``quantize`` result, for figures."""
    lut = np.array([[255, 255, 255], [255, 0, 0], [0, 0, 0]], np.uint8)
    return lut[labels]


def red_blocks(red: np.ndarray, block: int = BLOCK) -> np.ndarray:
    """(x, y) centres of every block×block window (stride 1) with > 50 % red pixels."""
    counts = cv2.boxFilter(red.astype(np.float32), -1, (block, block),
                           normalize=False, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
    h, w = red.shape
    counts = counts[: h - block + 1, : w - block + 1]
    ys, xs = np.nonzero(counts > 0.5 * block * block)
    return np.column_stack([xs + block // 2, ys + block // 2])


def _closest(points: np.ndarray, ref: tuple[float, float]) -> np.ndarray:
    d = (points[:, 0] - ref[0]) ** 2 + (points[:, 1] - ref[1]) ** 2
    return points[int(np.argmin(d))]


@dataclass
class Corners:
    tl: np.ndarray
    tr: np.ndarray
    bl: np.ndarray
    br: np.ndarray

    def as_array(self) -> np.ndarray:
        """4×2 array in the app/metadata order: TL, TR, BL, BR."""
        return np.array([self.tl, self.tr, self.bl, self.br])


def find_corners(roi_rgb: np.ndarray, band: int = BAND_PX) -> Corners | None:
    """Four label corners inside the ROI crop (ROI pixel coordinates), or None (Step 2 fails)."""
    H, W = roi_rgb.shape[:2]
    top = red_blocks(quantize(roi_rgb[:band]) == 1)
    bot = red_blocks(quantize(roi_rgb[H - band:]) == 1)
    if not (0 < len(top) <= MAX_BLOCKS and 0 < len(bot) <= MAX_BLOCKS):
        return None
    tl, tr = _closest(top, (0, 0)), _closest(top, (W, 0))
    bl, br = _closest(bot, (0, band)), _closest(bot, (W, band))
    off = np.array([0, H - band])
    return Corners(tl, tr, bl + off, br + off)
