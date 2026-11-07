"""Dataset paths and loaders. All paths are relative to the repository root."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def repo_root() -> Path:
    """Walk up from this file to the folder that holds ``pyproject.toml``."""
    for p in Path(__file__).resolve().parents:
        if (p / "pyproject.toml").exists():
            return p
    raise FileNotFoundError("pyproject.toml not found; install the repo with `pip install -e .`")


def data_dir() -> Path:
    """``$VISIONCRACK_DATA`` if set (relative paths are taken from the repo root), else ``<repo>/data/raw``."""
    env = os.environ.get("VISIONCRACK_DATA")
    if not env:
        return repo_root() / "data" / "raw"
    p = Path(env)
    return p if p.is_absolute() else repo_root() / p


def results_dir(kind: str = "figures") -> Path:
    d = repo_root() / "results" / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_rgb(path: str | Path) -> np.ndarray:
    """RGB image (JPEG or PNG)."""
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def load_table1() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (captures, inspectors). ``captures`` has an ``bbox`` column (4×2 array)."""
    d = data_dir() / "table1_et"
    caps = pd.read_csv(d / "metadata.csv")
    caps["path"] = caps["image"].map(lambda f: d / "images" / f)
    cols = ["tl_x", "tl_y", "tr_x", "tr_y", "bl_x", "bl_y", "br_x", "br_y"]
    caps["bbox"] = [r.reshape(4, 2) for r in caps[cols].to_numpy()]
    inspectors = pd.read_csv(d / "inspectors.csv", index_col="inspector")
    return caps, inspectors
