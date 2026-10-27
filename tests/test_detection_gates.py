import numpy as np
import pytest

import visioncrack as vc
from visioncrack import barcode, detection, gates
from visioncrack.io import data_dir
from visioncrack.metrics import half_up


def test_barcode_roundtrip():
    assert barcode.encode("lewb") == barcode.LABEL_1_LEWB
    assert barcode.decode(barcode.LABEL_1_LEWB) == ("lewb", True)
    assert barcode.decode(barcode.LABEL_26) == ("3D6m", True)


def test_gates_on_ideal_and_rotated_box():
    box = np.array([[0, 0], [100, 0], [0, 60], [100, 60]])
    assert gates.evaluate(box, 100, 60).accepted
    t = np.radians(3)
    rot = np.array([[0, 0], [100, 0], [60 * np.sin(t), 60], [100 + 60 * np.sin(t), 60]])
    g = gates.evaluate(rot, 100, 60)
    assert g.coverage_ok and not g.rotation_ok and g.first_failure == "rotation"
    assert gates.evaluate(None, 100, 60).first_failure == "corners"


def test_red_blocks_need_three_of_four():
    red = np.zeros((4, 4), bool)
    red[0, 0] = red[0, 1] = red[1, 0] = True        # 3 of 4 in the top-left window
    assert [1, 1] in detection.red_blocks(red).tolist()
    red[1, 0] = False                               # only 2 of 4
    assert detection.red_blocks(red).size == 0


def test_half_up():
    assert half_up([2.2085, 1.875, 0.0125], 3).tolist() == [2.209, 1.875, 0.013]


@pytest.mark.skipif(not (data_dir() / "table1_et").exists(), reason="dataset not downloaded")
def test_python_corners_match_app():
    caps, _ = vc.load_table1()
    roi = vc.preview_roi((2160, 3840), (430, 932))
    x0, y0, x1, y1 = roi.xyxy
    for p, bb in zip(caps.path, caps.bbox):
        c = detection.find_corners(vc.read_rgb(p)[y0:y1, x0:x1])
        assert np.abs(c.as_array() - bb).max() <= 2
