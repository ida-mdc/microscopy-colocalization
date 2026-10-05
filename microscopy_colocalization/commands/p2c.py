"""p2c: point-to-channel (CSV-to-image) distance, unchanged from
fish_colocalization's colocalize_image_to_csv.
"""
import logging
import os

import pandas as pd

from microscopy_colocalization import io_utils, readers
from microscopy_colocalization.commands.p2p import read_spots
from microscopy_colocalization.matching import get_spots_distances
from microscopy_colocalization.threshold import THRESHOLD_METHODS, get_distance_map, get_threshold


def add_arguments(parser):
    parser.description = (
        'Point-to-channel colocalization: threshold an image into a mask, then measure each '
        'point in a CSV (e.g. RS-FISH output) by its distance to the nearest masked object.'
    )
    parser.add_argument('-p', '--path', required=True,
                         help='Folder containing the images and CSVs (searched one level deep too).')
    parser.add_argument('-p1', '--pattern1', required=True,
                         help="Filename wildcard for the point CSV files, e.g. '*.csv'.")
    parser.add_argument('-p2', '--pattern2', default=None,
                         help="Filename wildcard for the image files, e.g. '*.tif'. If omitted, "
                              'scans for every supported image format '
                              f'({", ".join(readers.SUPPORTED_EXTENSIONS)}).')
    parser.add_argument('-c', '--channel', default=-1, type=int,
                         help='Index of the channel to use from each image, 0 means the first '
                              'channel in the file. Required if the images are multi-channel; '
                              'leave at the default -1 for plain 2D images with no channel axis.')
    parser.add_argument('-tm', '--threshold_method', default='otsu', choices=THRESHOLD_METHODS,
                         help='Method used to separate signal from background in the image '
                              '(default: otsu).')
    parser.set_defaults(func=run, _parser=parser)


def run(args):
    result_dir = io_utils.create_result_dir(args.path, prefix='p2c')
    io_utils.set_logger(result_dir)
    io_utils.save_args_to_file(args, result_dir)

    point_paths, image_paths = io_utils.resolve_sources(args.path, args.pattern1, None, args.pattern2)

    channel = None if args.channel == -1 else args.channel

    rows = pd.DataFrame(columns=['image_index', 'image_name', 'distance'])

    for ip, p in enumerate(image_paths):
        logging.info('Processing image %d out of %d. Name %s', ip, len(image_paths), os.path.basename(p))

        array, dim_order = readers.read_array(p)
        if 'C' in dim_order and channel is None:
            logging.warning('Skipping %s: image has a channel axis but --channel was not given.', p)
            continue
        img = readers.select_channel(array, dim_order, channel)

        thr = get_threshold(img, args.threshold_method)
        dist_map = get_distance_map(img, thr)

        spots = read_spots(point_paths[ip])
        if spots is None:
            continue
        if spots.shape[1] == 3:
            logging.warning('For image-csv colocalization expected csv without z column, '
                             'but z column was found.')

        distances = get_spots_distances(spots, dist_map)

        data_to_add = pd.DataFrame({
            'image_index': ip,
            'image_name': os.path.basename(p),
            'distance': distances,
        })
        rows = pd.concat([rows, data_to_add], ignore_index=True)

    rows.to_csv(os.path.join(result_dir, 'distances.csv'))
