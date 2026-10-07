"""p2p: point-to-point (CSV-to-CSV) spot matching, from fish_colocalization's
colocalize_csv_to_csv. --pattern replaces -p1/-p2 (2 patterns -> one pair, same as before;
3+ -> every pair, automatically), and --max_dist replaces --min_dist (it was always a maximum
distance for a match, never a minimum).
"""
import logging
import os

import pandas as pd

from microscopy_colocalization import io_utils
from microscopy_colocalization.matching import compare_spot_sets


def add_arguments(parser):
    parser.description = (
        'Point-to-point colocalization: match spot coordinates between two or more CSVs '
        '(e.g. RS-FISH output per channel) by nearest-neighbor distance.'
    )
    parser.add_argument('-p', '--path', required=True,
                         help='Folder containing the CSV files (searched one level deep too).')
    parser.add_argument('--pattern', action='append',
                         help="Filename wildcard for one group of CSVs, e.g. 'C1-*.csv'. Give "
                              "at least twice, e.g. --pattern 'C1-*.csv' --pattern 'C2-*.csv'. "
                              'With more than two, every unique pair is compared.')
    parser.add_argument('-d', '--max_dist', default=2, type=int,
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
    io_utils.require_min_items(args._parser, 'pattern', args.pattern)
    io_utils.reject_empty_patterns(args._parser, pattern=args.pattern)

    result_dir = io_utils.create_result_dir(args.path, prefix='p2p')
    io_utils.set_logger(result_dir)
    io_utils.save_args_to_file(args, result_dir)

    path_lists = io_utils.resolve_multi_patterns(args.path, args.pattern)
    n_images = len(path_lists[0])

    summary_rows = []
    for i, j in io_utils.all_pairs(range(len(args.pattern))):
        pattern_i, pattern_j = args.pattern[i], args.pattern[j]
        tag = io_utils.pattern_tag(pattern_i) + io_utils.pattern_tag(pattern_j)

        for ip in range(n_images):
            p, p_other = path_lists[i][ip], path_lists[j][ip]
            logging.info('Processing pair %s/%s, image %d out of %d. Name %s',
                         pattern_i, pattern_j, ip, n_images, os.path.basename(p))

            spots1 = read_spots(p)
            if spots1 is None:
                continue
            spots2 = read_spots(p_other)
            if spots2 is None:
                continue

            match_spots1, match_spots2, distances, mean_euc_dist = compare_spot_sets(
                spots1, spots2, args.max_dist)

            summary_rows.append({
                'pattern1': pattern_i,
                'pattern2': pattern_j,
                'image_name': os.path.basename(p),
                'n_points_1': len(spots1),
                'n_points_2': len(spots2),
                'n_matches': len(distances),
                'mean_euc_dist': round(mean_euc_dist, 4),
            })

            match_spots1 = [','.join(map(str, sublist)) for sublist in match_spots1]
            match_spots2 = [','.join(map(str, sublist)) for sublist in match_spots2]

            pd.DataFrame({
                'match_point_1': match_spots1,
                'match_point_2': match_spots2,
                'distance': distances,
            }).to_csv(os.path.join(result_dir, f'{tag}{ip}.csv'))

    pd.DataFrame(summary_rows, columns=['pattern1', 'pattern2', 'image_name', 'n_points_1',
                                        'n_points_2', 'n_matches', 'mean_euc_dist']
                ).to_csv(os.path.join(result_dir, 'summary.csv'))
