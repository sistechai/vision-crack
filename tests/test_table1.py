import numpy as np
import pytest

import visioncrack as vc
from visioncrack.io import data_dir
from visioncrack.width import dark_runs


def test_roi_matches_paper_device():
    roi = vc.preview_roi((2160, 3840), (430, 932))
    assert (roi.x, roi.y, roi.w, roi.h) == (682, 2884, 797, 478)


def test_dark_runs_ignores_short_runs():
    row = np.array([255] * 3 + [0] * 7 + [255] * 2 + [0] * 3 + [255] + [0] * 10)
    assert dark_runs(row) == [7, 10]


@pytest.mark.skipif(not (data_dir() / "table1_et").exists(), reason="dataset not downloaded")
def test_table1_regression():
    caps, _ = vc.load_table1()
    roi = vc.preview_roi((2160, 3840), (430, 932))
    R = np.array([vc.measure_capture(vc.read_rgb(p), b, roi).widths_mm
                  for p, b in zip(caps.path, caps.bbox)])
    # first capture = "VisionCrack 1" row of Table 1 (also the CI sample)
    assert np.allclose(R[0].round(3), [0.644, 1.066, 1.757, 2.229, 2.823])
    if len(R) == 10:   # full dataset
        assert np.allclose(R.mean(0).round(3), [0.652, 1.066, 1.745, 2.209, 2.814])
