"""Synthetic fixture builders and CLI test helpers shared across the test suite."""
import argparse

import numpy as np
import pandas as pd
import tifffile as tif


def run_cli(module, argv):
    """Parse argv through a command module's real add_arguments() and run it, exactly like
    __main__.py does for that subcommand.
    """
    parser = argparse.ArgumentParser()
    module.add_arguments(parser)
    args = parser.parse_args(argv)
    args.func(args)
    return args


def find_result_dir(path, prefix):
    results = sorted(path.glob(f'{prefix}_results_*'))
    assert len(results) == 1, f'expected exactly one {prefix}_results_* dir, found {results}'
    return results[0]


def write_multichannel_tif(path, n_channels=3, size=64, seed=0):
    """A (C, size, size) uint16 tif with one distinguishable bright square per channel, at a
    position that shifts with the channel index so channels are neither fully overlapping
    nor fully disjoint.
    """
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 50, size=(n_channels, size, size), dtype=np.uint16)
    for c in range(n_channels):
        start = 15 + 5 * c
        end = start + 10
        img[c, start:end, start:end] += 200
    tif.imwrite(path, img, photometric='minisblack')
    return img


def write_points_csv(path, points):
    """points: list of (y, x) tuples."""
    pd.DataFrame(points, columns=['y', 'x']).to_csv(path, index=False)
