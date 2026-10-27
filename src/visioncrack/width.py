"""Bar and crack width extraction (paper Sec. 2.3.1).

Pipeline: crop → grayscale → Gaussian blur → Otsu → per-scan-line dark runs
→ measurement matrix M → clipped column mean (mu_j).
"""

from __future__ import annotations

import cv2
import numpy as np

from .constants import CLIP_Z, GAUSSIAN_KSIZE, GAUSSIAN_SIGMA, MIN_RUN_PX


def blur_gray(rgb: np.ndarray, paper_compat: bool = True) -> np.ndarray:
    """Grayscale + Gaussian blur.

    ``paper_compat=True`` reproduces the published numbers. The original code passed
    an RGB array to ``COLOR_BGR2GRAY``, so the red and blue luminance weights were
    swapped (gray = 0.114 R + 0.587 G + 0.299 B). This shifts ET-1 by ~0.007 mm.
    Use ``False`` for the standard conversion.
    """
    code = cv2.COLOR_BGR2GRAY if paper_compat else cv2.COLOR_RGB2GRAY
    gray = cv2.cvtColor(rgb, code)
    return cv2.GaussianBlur(gray, GAUSSIAN_KSIZE, GAUSSIAN_SIGMA)


def binarize(gray: np.ndarray, thresh: float | None = None) -> tuple[float, np.ndarray]:
    """Otsu threshold (``thresh=None``) or a fixed threshold. Dark pixels → 0."""
    if thresh is None:
        return cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)
    return cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)


def dark_runs(row: np.ndarray, min_run: int = MIN_RUN_PX) -> list[int]:
    """Lengths of the dark (0) runs in one scan line that are longer than ``min_run``."""
    runs, x, n = [], 0, len(row)
    while x < n:
        count = 0
        while x < n and row[x] == 0:
            count += 1
            x += 1
        if count > min_run:
            runs.append(count)
        x += 1
    return runs


def measurement_matrix(binary: np.ndarray, n_bars: int,
                       min_run: int = MIN_RUN_PX) -> np.ndarray:
    """Matrix M (rows = scan lines, cols = bars) in pixels.

    Scan lines that don't show exactly ``n_bars`` bars (noise, edges, label text)
    are skipped.
    """
    rows = [r for r in (dark_runs(line, min_run) for line in binary) if len(r) == n_bars]
    if not rows:
        return np.empty((0, n_bars))
    return np.asarray(rows, dtype=float)


def clipped_mean(values: np.ndarray, z: float = CLIP_Z) -> float:
    """Mean after dropping values outside mean ± z·std."""
    values = np.asarray(values, dtype=float)
    m, s = values.mean(), values.std()
    kept = values[(values >= m - z * s) & (values <= m + z * s)]
    return float(kept.mean()) if kept.size else float(m)


def column_means(M: np.ndarray, z: float = CLIP_Z) -> np.ndarray:
    """mu_j for every column of M (paper Eq. 9, with outlier clipping)."""
    return np.array([clipped_mean(M[:, j], z) for j in range(M.shape[1])])
