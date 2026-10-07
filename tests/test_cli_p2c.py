import numpy as np
import pandas as pd
import pytest
import tifffile as tif

from microscopy_colocalization.commands import p2c

from .helpers import find_result_dir, run_cli, write_points_csv


def _write_2d_fixture(tmp_path):
    img = np.zeros((64, 64), dtype=np.uint16)
    img[20:30, 20:30] = 200
    tif.imwrite(tmp_path / 'img1.tif', img)
    write_points_csv(tmp_path / 'img1.csv', [(25.3, 25.3), (5.3, 5.3)])


@pytest.mark.parametrize('pattern2', ['*.tif', None])
def test_p2c_distances_explicit_and_default_pattern2(tmp_path, pattern2):
    _write_2d_fixture(tmp_path)

    argv = ['-p', str(tmp_path), '-p1', '*.csv']
    if pattern2 is not None:
        argv += ['-p2', pattern2]
    run_cli(p2c, argv)

    distances = pd.read_csv(find_result_dir(tmp_path, 'p2c') / 'distances.csv')['distance']
    assert sorted(distances) == pytest.approx([0.0, 20.794], abs=1e-3)


def test_p2c_uses_the_explicitly_given_channel_on_a_3d_image(tmp_path):
    """Regression test: the original silently skipped 3D images whenever an explicit channel
    was given (and only worked via a since-fixed negative-index fallback). Must use channel 1
    correctly here, not skip the image.
    """
    img = np.zeros((3, 64, 64), dtype=np.uint16)
    img[1, 20:30, 20:30] = 200  # bright object only in channel 1
    tif.imwrite(tmp_path / 'img1.tif', img, photometric='minisblack')
    write_points_csv(tmp_path / 'img1.csv', [(25.0, 25.0)])

    run_cli(p2c, ['-p', str(tmp_path), '-p1', '*.csv', '-p2', '*.tif', '-c', '1'])

    distances = pd.read_csv(find_result_dir(tmp_path, 'p2c') / 'distances.csv')
    assert distances['distance'].iloc[0] == pytest.approx(0.0)


def test_p2c_rejects_empty_pattern(tmp_path):
    with pytest.raises(SystemExit):
        run_cli(p2c, ['-p', str(tmp_path), '-p1', ''])
