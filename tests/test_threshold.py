import numpy as np
import pytest

from microscopy_colocalization.threshold import THRESHOLD_METHODS, get_distance_map, get_threshold


@pytest.fixture
def bimodal_image():
    img = np.zeros((20, 20), dtype=np.uint16)
    img[2:5, 2:5] = 200  # small bright foreground block, background is 0
    return img


@pytest.mark.parametrize('method', THRESHOLD_METHODS)
def test_get_threshold_separates_bimodal_image(bimodal_image, method):
    thr = get_threshold(bimodal_image, method)
    assert 0 <= thr < 200


def test_get_threshold_rejects_unknown_method(bimodal_image):
    with pytest.raises(ValueError):
        get_threshold(bimodal_image, 'not-a-method')


def test_get_distance_map_zero_at_foreground_and_correct_at_background(bimodal_image):
    dist_map = get_distance_map(bimodal_image, thr=100)
    assert dist_map[3, 3] == 0  # inside the foreground block
    assert dist_map[0, 0] == pytest.approx(np.sqrt(2 ** 2 + 2 ** 2))  # nearest corner of the block


def test_get_distance_map_warns_when_foreground_dominates(caplog):
    mostly_bright = np.full((10, 10), 200, dtype=np.uint16)
    with caplog.at_level('WARNING'):
        get_distance_map(mostly_bright, thr=100)
    assert any('more foreground than background' in r.message for r in caplog.records)


def test_get_distance_map_silent_when_background_dominates(bimodal_image, caplog):
    with caplog.at_level('WARNING'):
        get_distance_map(bimodal_image, thr=100)
    assert not caplog.records
