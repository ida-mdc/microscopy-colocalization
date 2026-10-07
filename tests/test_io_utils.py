from pathlib import Path

import pytest

from microscopy_colocalization import io_utils


class _FakeParser:
    """Mimics the one bit of argparse.ArgumentParser's behavior these helpers rely on."""
    def error(self, message):
        raise SystemExit(message)


@pytest.mark.parametrize('pattern, expected_tag', [
    ('C1-*.csv', 'C1-'),
    ('*.tif', '.tif'),
    ('img_?.png', 'img_'),
    ('C[12]-*.csv', 'C12-'),
])
def test_pattern_tag(pattern, expected_tag):
    assert io_utils.pattern_tag(pattern) == expected_tag


def test_all_pairs_unique_combinations():
    assert io_utils.all_pairs([0, 1, 2]) == [(0, 1), (0, 2), (1, 2)]


@pytest.mark.parametrize('items', [[0], [], [0, 0, 1]])
def test_require_min_items_rejects_too_few_or_duplicates(items):
    with pytest.raises(SystemExit):
        io_utils.require_min_items(_FakeParser(), 'x', items)


def test_require_min_items_accepts_enough_unique_items():
    io_utils.require_min_items(_FakeParser(), 'x', [0, 1, 2])  # should not raise


@pytest.mark.parametrize('value', ['', ['a', '']])
def test_reject_empty_patterns_rejects_empty_string(value):
    with pytest.raises(SystemExit):
        io_utils.reject_empty_patterns(_FakeParser(), p=value)


@pytest.mark.parametrize('value', ['a', ['a', 'b']])
def test_reject_empty_patterns_accepts_nonempty(value):
    io_utils.reject_empty_patterns(_FakeParser(), p=value)  # should not raise


@pytest.mark.parametrize('path, expected', [
    ('condA/img1.tif', ('condA', None, 'img1')),
    ('condA/run1/img1.tif', ('condA', 'run1', 'img1')),
])
def test_paths_to_df_parses_condition_run_layout(path, expected):
    df = io_utils.paths_to_df([path])
    row = df.iloc[0]
    assert (row['condition'], row['run'], row['filename']) == expected


def test_create_result_dir_creates_and_returns_a_subdir(tmp_path):
    result_dir = io_utils.create_result_dir(str(tmp_path), prefix='test')
    assert result_dir.startswith(str(tmp_path))
    assert 'test_results_' in result_dir
    assert Path(result_dir).is_dir()


def test_resolve_multi_patterns_requires_equal_counts(tmp_path):
    (tmp_path / 'a1.csv').write_text('y,x\n1,1\n')
    (tmp_path / 'b1.csv').write_text('y,x\n1,1\n')
    (tmp_path / 'b2.csv').write_text('y,x\n1,1\n')
    with pytest.raises(ValueError):
        io_utils.resolve_multi_patterns(str(tmp_path), ['a*.csv', 'b*.csv'])


def test_resolve_multi_patterns_matches_equal_counts(tmp_path):
    (tmp_path / 'a1.csv').write_text('y,x\n1,1\n')
    (tmp_path / 'b1.csv').write_text('y,x\n1,1\n')
    path_lists = io_utils.resolve_multi_patterns(str(tmp_path), ['a*.csv', 'b*.csv'])
    assert [len(paths) for paths in path_lists] == [1, 1]
