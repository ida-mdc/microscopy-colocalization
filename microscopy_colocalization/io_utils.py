"""Result-dir/logging/arg-saving scaffolding (from fish_colocalization) plus unified
dir/pattern/channel source discovery covering every input layout the old repos supported:

- same file, two channels        (dir1==dir2, pattern1==pattern2, channel1 != channel2)
- same folder, two wildcards      (dir1==dir2, pattern1 != pattern2)
- two different folders           (dir1 != dir2)
"""
import itertools
import logging
import os
import re
from datetime import datetime
from glob import glob

import pandas as pd

from microscopy_colocalization.readers import SUPPORTED_EXTENSIONS


def create_result_dir(path, prefix='colocalization'):
    now = datetime.now()
    timestamp_str = now.strftime('%Y%m%d_%H%M%S')
    result_path = os.path.join(path, f'{prefix}_results_{timestamp_str}')
    os.makedirs(result_path)
    return result_path


def set_logger(result_path):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(os.path.join(result_path, 'logfile.log'))
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info('Starting')


def reject_empty_patterns(parser, **patterns):
    """Error out on an explicit empty-string pattern (e.g. -p1 '' or --pattern ''), which
    argparse's required=True does not catch and which would otherwise silently default to
    scanning every supported image extension instead of matching nothing, as the user likely
    intended. Each kwarg value may be a single string or a list of strings.
    """
    for name, value in patterns.items():
        values = value if isinstance(value, list) else [value]
        if any(v == '' for v in values):
            parser.error(f"--{name} cannot be an empty string.")


def require_min_items(parser, name, items, minimum=2):
    """Error out unless an action='append' list argument got at least `minimum` values."""
    if items is None or len(items) < minimum:
        parser.error(f'--{name} requires at least {minimum} values (give it multiple times, '
                     f'e.g. --{name} a --{name} b).')
    if len(set(items)) != len(items):
        parser.error(f'--{name} values must be unique.')


def save_args_to_file(args, result_path, filename='arguments.txt'):
    """Dump user-facing CLI args. Skips internal bookkeeping (func/parser refs set via
    parser.set_defaults for dispatch/validation) that isn't meaningful to a reader.
    """
    with open(os.path.join(result_path, filename), 'w') as file:
        for arg, value in vars(args).items():
            if arg == 'func' or arg.startswith('_'):
                continue
            file.write(f'{arg}: {value}\n')


def _default_image_patterns():
    return [f'*.{ext}' for ext in SUPPORTED_EXTENSIONS]


def _glob_paths(input_path, pattern):
    """Glob one pattern, or every pattern in a list, at the top level and one level deep."""
    patterns = pattern if isinstance(pattern, list) else [pattern]
    paths = []
    for p in patterns:
        paths.extend(glob(os.path.join(input_path, p)))
        paths.extend(glob(os.path.join(input_path, '*', p)))
    return sorted(paths)


def get_paths_lists(input_path, pattern1, pattern2):
    """Two glob-matched, paired file lists (today's p2p/p2c discovery mechanism)."""
    paths1 = _glob_paths(input_path, pattern1)
    paths2 = _glob_paths(input_path, pattern2)

    if len(paths1) != len(paths2):
        raise ValueError('The lengths of the two file path lists do not match.')

    logging.info('PLEASE REVIEW THE PAIRS OF FILES TO COLOCALIZE:')
    for item1, item2 in zip(paths1, paths2):
        logging.info('Pair:\n%s,\n%s', os.path.basename(item1), os.path.basename(item2))

    return paths1, paths2


def resolve_sources(dir1, pattern1, dir2, pattern2):
    """Resolve two (dir, pattern) specs into paired file-path lists, covering all three
    layouts: same file/different channel (caller distinguishes via channel index, not here),
    same folder/different patterns, and different folders.

    Either pattern being None scans every extension readers.py supports instead of one fixed
    pattern (c2c's -ext default behavior, mirrored here for p2c's image side).
    """
    dir2 = dir1 if dir2 is None else dir2
    pattern1 = _default_image_patterns() if pattern1 is None else pattern1
    pattern2 = _default_image_patterns() if pattern2 is None else pattern2
    return get_paths_lists(dir1, pattern1, pattern2) if dir1 == dir2 else (
        _glob_paths(dir1, pattern1),
        _glob_paths(dir2, pattern2),
    )


def get_all_image_paths(path, ext=None):
    """Recursive directory-tree walk (today's c2c discovery mechanism).

    If ext is None, scans every extension readers.py supports instead of one fixed type.
    """
    extensions = [ext] if ext else SUPPORTED_EXTENSIONS

    paths = []
    for e in extensions:
        pattern = os.path.join(path, '**', f'*.{e}')
        paths.extend(glob(pattern, recursive=True))
    return sorted(os.path.relpath(p, path) for p in paths)


def paths_to_df(paths):
    """Parse condition/[run/]filename.ext relative paths into a DataFrame (today's c2c layout)."""
    data = []
    for p in paths:
        parts = p.split(os.sep)
        if len(parts) == 2:
            condition, filename_with_ext = parts
            filename = os.path.splitext(filename_with_ext)[0]
            data.append((p, condition, None, filename))
        elif len(parts) == 3:
            condition, run, filename_with_ext = parts
            filename = os.path.splitext(filename_with_ext)[0]
            data.append((p, condition, run, filename))

    return pd.DataFrame(data, columns=['path', 'condition', 'run', 'filename'])


def all_pairs(items):
    """All unique (a, b) pairs from items, a before b in the input order."""
    return list(itertools.combinations(items, 2))


def pattern_tag(pattern):
    """Turn a glob wildcard into a filesystem-safe label, e.g. 'C1-*.csv' -> 'C1-'."""
    stem = re.sub(r'[*?\[\]]', '', pattern)
    return os.path.splitext(stem)[0]


def resolve_multi_patterns(path, patterns):
    """Glob N patterns under `path` (top level and one level deep), requiring every pattern
    to match the same number of files (one list per pattern, index-aligned across patterns).
    """
    path_lists = [_glob_paths(path, p) for p in patterns]

    lengths = {len(paths) for paths in path_lists}
    if len(lengths) > 1:
        counts = ', '.join(f"'{p}': {len(paths)}" for p, paths in zip(patterns, path_lists))
        raise ValueError(f'All patterns must match the same number of files. Got {counts}.')

    for pattern, paths in zip(patterns, path_lists):
        logging.info("Pattern '%s' matched %d file(s).", pattern, len(paths))

    return path_lists
