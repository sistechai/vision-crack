"""Geometric error model (paper Sec. *Geometric sensitivity of the single-axis scale*)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def tilt_scale_error(phi_deg, exact: bool = True):
    """Relative scale error from out-of-plane tilt φ (Eq. tilt_error).

    exact: Δs/s = 1/cos φ − 1;   approximate: φ²/2 (φ in radians).
    """
    phi = np.radians(np.asarray(phi_deg, float))
    return 1 / np.cos(phi) - 1 if exact else phi ** 2 / 2


@dataclass
class TiltFit:
    w0: float          # tilt-independent error (mm): additive edge term
    k: float           # tilt sensitivity (mm)
    r2: float
    n: int

    def predict(self, phi_deg):
        return self.w0 + self.k * (1 - np.cos(np.radians(np.asarray(phi_deg, float))))

    def phi_at(self, mae_mm: float) -> float:
        """Tilt (deg) at which the model reaches ``mae_mm``; nan if never."""
        c = 1 - (mae_mm - self.w0) / self.k if self.k > 0 else np.nan
        return float(np.degrees(np.arccos(c))) if -1 <= c <= 1 else float("nan")


def fit_tilt_model(phi_deg, mae_mm) -> TiltFit:
    """Least-squares fit of MAE(φ) = w0 + k·(1 − cos φ) (Eq. tilt_fit)."""
    x = 1 - np.cos(np.radians(np.asarray(phi_deg, float)))
    y = np.asarray(mae_mm, float)
    w0, k = np.linalg.lstsq(np.c_[np.ones_like(x), x], y, rcond=None)[0]
    r2 = 1 - ((y - w0 - k * x) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return TiltFit(float(w0), float(k), float(r2), len(y))
