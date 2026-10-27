"""Error summaries for Table 1."""

from __future__ import annotations

import numpy as np
import pandas as pd


def half_up(values, nd: int) -> np.ndarray:
    """Round half away from zero, as in the published tables (NumPy rounds half to even)."""
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal(1).scaleb(-nd)
    flat = [float(Decimal(repr(float(x))).quantize(q, ROUND_HALF_UP)) for x in np.ravel(values)]
    return np.reshape(flat, np.shape(values))


def table1_summary(readings: np.ndarray, gt: np.ndarray) -> pd.DataFrame:
    """Summary rows exactly as defined in the paper's Table 1.

    readings: (n_repeats, n_targets) in mm.
    - ``mean``     : per-target mean (the row labelled "MAE*" in the paper)
    - ``std``      : per-target population std (ddof=0)
    - ``abs_bias`` : |mean - GT| (the row labelled "MAE* vs. GT")
    The "Overall" column is the mean across targets.
    """
    readings, gt = np.asarray(readings, float), np.asarray(gt, float)
    mean = readings.mean(axis=0)
    rows = {
        "mean": mean,
        "std": readings.std(axis=0),
        "abs_bias": np.abs(mean - gt),
    }
    df = pd.DataFrame(rows).T
    df.columns = [f"ET-{i + 1}" for i in range(len(gt))]
    df["Overall"] = df.mean(axis=1)
    return df


def per_reading_error(readings: np.ndarray, gt: np.ndarray) -> pd.DataFrame:
    """Error computed from every single reading, not from the per-target mean.

    Rows (per target, then "Overall" = mean over targets):
    - ``mae``  : mean |reading − GT|, the usual MAE (≥ the paper's |mean − GT|)
    - ``bias`` : mean (reading − GT), signed; shows the direction of systematic error
    - ``rmse`` : sqrt(mean (reading − GT)²)
    """
    readings, gt = np.asarray(readings, float), np.asarray(gt, float)
    err = readings - gt
    df = pd.DataFrame({
        "mae": np.abs(err).mean(axis=0),
        "bias": err.mean(axis=0),
        "rmse": np.sqrt((err ** 2).mean(axis=0)),
    }).T
    df.columns = [f"ET-{i + 1}" for i in range(len(gt))]
    df["Overall"] = df.mean(axis=1)
    return df
