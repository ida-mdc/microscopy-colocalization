from itertools import combinations

import pandas as pd
import pytest

from microscopy_colocalization.commands import c2c

from .helpers import find_result_dir, run_cli, write_multichannel_tif


@pytest.mark.parametrize('channels', [[0, 1], [0, 1, 2]])
def test_c2c_produces_one_row_and_one_plot_per_pair(tmp_path, channels):
    cond_dir = tmp_path / 'condA'
    cond_dir.mkdir()
    write_multichannel_tif(cond_dir / 'img1.tif', n_channels=3)

    argv = ['-p', str(tmp_path)]
    for c in channels:
        argv += ['-c', str(c)]
    run_cli(c2c, argv)

    result_dir = find_result_dir(tmp_path, 'c2c')
    stats = pd.read_csv(result_dir / 'stats.csv')

    expected_pairs = set(combinations(channels, 2))
    actual_pairs = set(zip(stats['channel1'], stats['channel2']))
    assert actual_pairs == expected_pairs

    for c1, c2_ in expected_pairs:
        assert (result_dir / f'manders_boxplot_c{c1}_c{c2_}.png').exists()
        assert (result_dir / f'img1_c{c1}_c{c2_}_overlap_mask.tif').exists()


def test_c2c_channel_index_actually_affects_result(tmp_path):
    """Regression test for the original's hardcoded-channel-2 bug: results for different
    channel pairs on the same image must actually differ. Uses two separate --path
    directories since two runs against the same one within the same wall-clock second would
    collide on the (inherited, second-resolution) timestamped result-dir name.
    """
    for run in ('run1', 'run2'):
        cond_dir = tmp_path / run / 'condA'
        cond_dir.mkdir(parents=True)
        write_multichannel_tif(cond_dir / 'img1.tif', n_channels=3)

    run_cli(c2c, ['-p', str(tmp_path / 'run1'), '-c', '0', '-c', '1'])
    stats_01 = pd.read_csv(find_result_dir(tmp_path / 'run1', 'c2c') / 'stats.csv')

    run_cli(c2c, ['-p', str(tmp_path / 'run2'), '-c', '0', '-c', '2'])
    stats_02 = pd.read_csv(find_result_dir(tmp_path / 'run2', 'c2c') / 'stats.csv')

    assert stats_01.iloc[0]['M1'] != stats_02.iloc[0]['M1']


@pytest.mark.parametrize('argv_extra', [
    ['-c', '0'],  # only one channel
    ['-c', '0', '-c', '0'],  # duplicate
])
def test_c2c_rejects_invalid_channel_args(tmp_path, argv_extra):
    with pytest.raises(SystemExit):
        run_cli(c2c, ['-p', str(tmp_path)] + argv_extra)


def test_c2c_default_extension_scans_without_minus_ext(tmp_path):
    cond_dir = tmp_path / 'condA'
    cond_dir.mkdir()
    write_multichannel_tif(cond_dir / 'img1.tif', n_channels=2)

    run_cli(c2c, ['-p', str(tmp_path), '-c', '0', '-c', '1'])  # no -ext given

    stats = pd.read_csv(find_result_dir(tmp_path, 'c2c') / 'stats.csv')
    assert len(stats) == 1
