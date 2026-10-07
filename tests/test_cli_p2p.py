from itertools import combinations

import pandas as pd
import pytest

from microscopy_colocalization.commands import p2p

from .helpers import find_result_dir, run_cli, write_points_csv

# Shared geometry across tests: C1/C2 have two close pairs + one far outlier each;
# C3 is close to C1's points but far from C2's, so pair-specific match counts differ.
_POINTS = {
    'C1': [(10, 10), (20, 20), (90, 90)],
    'C2': [(10.5, 10.5), (20.5, 20.5), (5, 5)],
    'C3': [(10.2, 10.2), (19.8, 19.8), (70, 70)],
}


def _write_fixture(tmp_path, groups):
    for group in groups:
        write_points_csv(tmp_path / f'{group}-img1.csv', _POINTS[group])


@pytest.mark.parametrize('groups', [['C1', 'C2'], ['C1', 'C2', 'C3']])
def test_p2p_produces_one_summary_row_and_one_file_per_pair(tmp_path, groups):
    _write_fixture(tmp_path, groups)

    argv = ['-p', str(tmp_path)]
    for g in groups:
        argv += ['--pattern', f'{g}-*.csv']
    run_cli(p2p, argv)

    result_dir = find_result_dir(tmp_path, 'p2p')
    summary = pd.read_csv(result_dir / 'summary.csv')

    expected_pairs = set(combinations(groups, 2))
    actual_pairs = set(zip(summary['pattern1'].str.split('-').str[0],
                           summary['pattern2'].str.split('-').str[0]))
    assert actual_pairs == expected_pairs

    for g1, g2 in expected_pairs:
        assert (result_dir / f'{g1}-{g2}-0.csv').exists()


def test_p2p_c1_c2_match_count_and_mean_distance(tmp_path):
    _write_fixture(tmp_path, ['C1', 'C2'])
    run_cli(p2p, ['-p', str(tmp_path), '--pattern', 'C1-*.csv', '--pattern', 'C2-*.csv', '-d', '2'])

    summary = pd.read_csv(find_result_dir(tmp_path, 'p2p') / 'summary.csv')
    row = summary.iloc[0]
    assert row['n_matches'] == 2
    assert row['mean_euc_dist'] == pytest.approx(0.7071, abs=1e-3)


@pytest.mark.parametrize('argv_extra', [
    ['--pattern', 'C1-*.csv'],  # only one pattern
    ['--pattern', 'C1-*.csv', '--pattern', 'C1-*.csv'],  # duplicate
    ['--pattern', 'C1-*.csv', '--pattern', ''],  # empty
])
def test_p2p_rejects_invalid_pattern_args(tmp_path, argv_extra):
    with pytest.raises(SystemExit):
        run_cli(p2p, ['-p', str(tmp_path)] + argv_extra)
