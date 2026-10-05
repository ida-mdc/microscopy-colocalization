"""Result-dir/logging/arg-saving scaffolding (from fish_colocalization) plus unified
dir/pattern/channel source discovery covering every input layout the old repos supported:

- same file, two channels        (dir1==dir2, pattern1==pattern2, channel1 != channel2)
- same folder, two wildcards      (dir1==dir2, pattern1 != pattern2)
- two different folders           (dir1 != dir2)
"""
import itertools
import logging
import os
from datetime import datetime
from glob import glob

import pandas as pd


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
    from microscopy_colocalization.readers import SUPPORTED_EXTENSIONS
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
    """Two glob-matched, paired file lists (today's p2p/c2p discovery mechanism)."""
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

    pattern1=None scans every extension readers.py supports instead of one fixed pattern
    (c2c's -ext default behavior, mirrored here for c2p's image side).
    """
    dir2 = dir2 or dir1
    pattern1 = pattern1 or _default_image_patterns()
    pattern2 = pattern2 or pattern1
    return get_paths_lists(dir1, pattern1, pattern2) if dir1 == dir2 else (
        _glob_paths(dir1, pattern1),
        _glob_paths(dir2, pattern2),
    )


def get_all_image_paths(path, ext=None):
    """Recursive directory-tree walk (today's c2c discovery mechanism).

    If ext is None, scans every extension readers.py supports instead of one fixed type.
    """
    from microscopy_colocalization.readers import SUPPORTED_EXTENSIONS
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


def channel_pairs(n_channels):
    """All unique (i, j) channel-index pairs, i < j, for --all-channel-pairs."""
    return list(itertools.combinations(range(n_channels), 2))
