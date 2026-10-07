"""p2p: point-to-point (CSV-to-CSV) spot matching, unchanged from
fish_colocalization's colocalize_csv_to_csv.
"""
import logging
import os

import pandas as pd

from microscopy_colocalization import io_utils
from microscopy_colocalization.matching import compare_spot_sets


def add_arguments(parser):
    parser.description = (
        'Point-to-point colocalization: match spot coordinates between two CSVs '
        '(e.g. RS-FISH output for two channels) by nearest-neighbor distance.'
    )
    parser.add_argument('-p', '--path', required=True,
                         help='Folder containing the CSV files (searched one level deep too).')
    parser.add_argument('-p1', '--pattern1', required=True,
                         help="Filename wildcard for the first group of CSVs, e.g. 'C1-*.csv'.")
    parser.add_argument('-p2', '--pattern2', required=True,
                         help="Filename wildcard for the second group of CSVs, e.g. 'C2-*.csv'.")
    parser.add_argument('-d', '--min_dist', default=2, type=int,
                         help='Maximum distance (pixels) between two points for them to count '
                              'as a match (default: 2).')
    parser.set_defaults(func=run, _parser=parser)


def read_spots(csv_path):
    try:
        df = pd.read_csv(csv_path)
    except (FileNotFoundError, IndexError):
        logging.warning('Skipping %s: csv is missing.', csv_path)
        return None
    return df[['y', 'x', 'z']].to_numpy() if 'z' in df.columns else df[['y', 'x']].to_numpy()


def run(args):
    io_utils.reject_empty_patterns(args._parser, pattern1=args.pattern1, pattern2=args.pattern2)

    result_dir = io_utils.create_result_dir(args.path, prefix='p2p')
    io_utils.set_logger(result_dir)
    io_utils.save_args_to_file(args, result_dir)

    paths1, paths2 = io_utils.resolve_sources(args.path, args.pattern1, None, args.pattern2)

    summary = pd.DataFrame(columns=['image_name', 'n_points_1', 'n_points_2', 'n_matches', 'mean_euc_dist'])

    for ip, p in enumerate(paths1):
        logging.info('Processing image %d out of %d. Name %s', ip, len(paths1), os.path.basename(p))

        spots1 = read_spots(p)
        if spots1 is None:
            continue
        spots2 = read_spots(paths2[ip])
        if spots2 is None:
            continue

        match_spots1, match_spots2, distances, mean_euc_dist = compare_spot_sets(spots1, spots2, args.min_dist)

        summary.loc[ip] = [os.path.basename(p), len(spots1), len(spots2), len(distances), round(mean_euc_dist, 4)]

        match_spots1 = [','.join(map(str, sublist)) for sublist in match_spots1]
        match_spots2 = [','.join(map(str, sublist)) for sublist in match_spots2]

        pd.DataFrame({
            'match_point_1': match_spots1,
            'match_point_2': match_spots2,
            'distance': distances,
        }).to_csv(os.path.join(result_dir, f'{ip}.csv'))

    summary.to_csv(os.path.join(result_dir, 'summary.csv'))
