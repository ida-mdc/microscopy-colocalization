import numpy as np
import pytest

from microscopy_colocalization.matching import compare_spot_sets, get_spots_distances
from microscopy_colocalization.threshold import get_distance_map, get_threshold


@pytest.mark.parametrize('set1, set2, min_dist, expected_n_matches', [
    # perfectly coincident points: both match
    ([[10, 10], [20, 20]], [[10, 10], [20, 20]], 2, 2),
    # within min_dist: both match
    ([[10, 10], [20, 20]], [[10.5, 10.5], [20.5, 20.5]], 2, 2),
    # farther than min_dist: no match
    ([[10, 10]], [[50, 50]], 2, 0),
    # one far outlier in set2 has no counterpart within range: only the close pair matches
    ([[10, 10], [20, 20]], [[10.5, 10.5], [20.5, 20.5], [90, 90]], 2, 2),
    # two set1 points both near one set2 point: greedy claims the closer one only
    ([[10, 10], [10.3, 10.3]], [[10, 10]], 1, 1),
])
def test_compare_spot_sets_match_counts(set1, set2, min_dist, expected_n_matches):
    matched1, matched2, distances, _ = compare_spot_sets(
        np.array(set1, dtype=float), np.array(set2, dtype=float), min_dist)
    assert len(distances) == expected_n_matches
    assert len(matched1) == expected_n_matches
    assert len(matched2) == expected_n_matches


def test_compare_spot_sets_contested_point_keeps_the_closer_one():
    set1 = np.array([[10.0, 10.0], [10.3, 10.3]])
    set2 = np.array([[10.0, 10.0]])
    matched1, _, _, _ = compare_spot_sets(set1, set2, min_dist=1)
    assert matched1.tolist() == [[10.0, 10.0]]


def test_compare_spot_sets_mean_distance():
    set1 = np.array([[0.0, 0.0], [10.0, 10.0]])
    set2 = np.array([[0.0, 1.0], [10.0, 12.0]])
    _, _, distances, mean_dist = compare_spot_sets(set1, set2, min_dist=5)
    assert mean_dist == pytest.approx(np.mean(distances))


def test_get_spots_distances_integer_coordinate_regression():
    """Regression test: the original bilinear-interpolation formula collapsed to 0 for any
    spot at an exact integer coordinate (x2==ceil(x)==x1). Must return the real distance.
    """
    img = np.zeros((64, 64), dtype=np.uint16)
    img[20:30, 20:30] = 200
    dist_map = get_distance_map(img, thr=get_threshold(img, 'otsu'))

    far_point = np.array([[5.0, 5.0]])
    distances = get_spots_distances(far_point, dist_map)
    assert distances[0] == pytest.approx(dist_map[5, 5])
    assert distances[0] > 0


def test_get_spots_distances_fractional_coordinate_interpolates():
    dist_map = np.array([[0.0, 10.0], [20.0, 30.0]])
    # exactly at the center of the 2x2 block -> average of all four corners
    distances = get_spots_distances(np.array([[0.5, 0.5]]), dist_map)
    assert distances[0] == pytest.approx(15.0)


def test_get_spots_distances_clamps_at_array_edge():
    dist_map = np.array([[0.0, 10.0], [20.0, 30.0]])
    distances = get_spots_distances(np.array([[1.0, 1.0]]), dist_map)  # last valid index
    assert distances[0] == pytest.approx(30.0)
