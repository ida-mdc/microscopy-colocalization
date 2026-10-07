"""c2c: channel-to-channel colocalization (Manders' overlap coefficients), from
channel_colocalization/colocalization.py, migrated onto the shared multi-format reader.
The only logic change from the original is using args.channel2 instead of a hardcoded
channel index, which silently ignored the --channel2/-c2i flag.
"""
import logging
import os

import numpy as np
import pandas as pd
import tifffile as tif

from microscopy_colocalization import io_utils, readers
from microscopy_colocalization.plotting import plot_and_save_manders
from microscopy_colocalization.threshold import THRESHOLD_METHODS, get_threshold


def add_arguments(parser):
    parser.description = (
        "Channel-to-channel colocalization: threshold two channels of the same multi-channel "
        "image and report Manders' M1/M2 overlap coefficients."
    )
    parser.add_argument('-p', '--path', required=True,
                         help='Root folder of images, laid out as condition/file or '
                              'condition/run/file (one or more conditions, each a subfolder).')
    parser.add_argument('-ext', '--extension', default=None,
                         help='Image file extension to look for, e.g. tif, czi, ims (no dot). '
                              'If omitted, scans for every supported format '
                              f'({", ".join(readers.SUPPORTED_EXTENSIONS)}).')
    parser.add_argument('-c1i', '--channel1', type=int,
                         help='Index of the first channel to compare, 0 means the first '
                              'channel in the file. Required unless --all-channel-pairs is set.')
    parser.add_argument('-c2i', '--channel2', type=int,
                         help='Index of the second channel to compare. Required unless '
                              '--all-channel-pairs is set.')
    parser.add_argument('-c1c', '--color1', default='green',
                         help='Display color for channel 1 in the output plot (default: green).')
    parser.add_argument('-c2c', '--color2', default='yellow',
                         help='Display color for channel 2 in the output plot (default: yellow).')
    parser.add_argument('-tm', '--threshold_method', default='otsu', choices=THRESHOLD_METHODS,
                         help='Method used to separate signal from background in each channel '
                              '(default: otsu).')
    parser.add_argument('--all-channel-pairs', action='store_true',
                         help='Run every unique pair of channels found in each image instead of '
                              'a single fixed pair. Cannot be combined with --channel1/--channel2.')
    parser.set_defaults(func=run, _parser=parser)


def get_thresholded_gray_image(image, thr):
    return np.where(image < thr, 0, image)


def get_images_for_manders(image1, image2, thr1, thr2):
    image1_thresholded = get_thresholded_gray_image(image1, thr1)
    image2_thresholded = get_thresholded_gray_image(image2, thr2)
    overlap_mask = (image1_thresholded != 0) & (image2_thresholded != 0)
    return image1_thresholded, image2_thresholded, overlap_mask


def save_manders_images(image1_thresholded, image2_thresholded, overlap_mask, result_dir, filename):
    tif.imwrite(os.path.join(result_dir, f'{filename}_thresholded1.tif'), image1_thresholded)
    tif.imwrite(os.path.join(result_dir, f'{filename}_thresholded2.tif'), image2_thresholded)
    tif.imwrite(os.path.join(result_dir, f'{filename}_overlap_mask.tif'), overlap_mask.astype(np.uint8))


def manders_coefficients(image1, image2, thr1, thr2, result_dir, filename):
    """Calculate Manders' M1/M2 overlap coefficients for two channels."""
    image1_thresholded, image2_thresholded, overlap_mask = get_images_for_manders(image1, image2, thr1, thr2)

    save_manders_images(image1_thresholded, image2_thresholded, overlap_mask, result_dir, filename)

    sum1 = np.sum(image1_thresholded)
    sum2 = np.sum(image2_thresholded)
    sum_overlap1 = np.sum(image1[overlap_mask])
    sum_overlap2 = np.sum(image2[overlap_mask])

    m1 = sum_overlap1 / sum1 if sum1 > 0 else 0
    m2 = sum_overlap2 / sum2 if sum2 > 0 else 0

    return m1, m2


def _validate_args(args):
    if args.all_channel_pairs:
        if args.channel1 is not None or args.channel2 is not None:
            args._parser.error('--channel1/--channel2 cannot be combined with --all-channel-pairs.')
    elif args.channel1 is None or args.channel2 is None:
        args._parser.error('--channel1 and --channel2 are both required unless --all-channel-pairs is set.')


def run(args):
    _validate_args(args)

    result_dir = io_utils.create_result_dir(args.path, prefix='c2c')
    io_utils.set_logger(result_dir)
    io_utils.save_args_to_file(args, result_dir)

    paths = io_utils.get_all_image_paths(args.path, args.extension)
    df = io_utils.paths_to_df(paths)

    rows = []
    for i in df.index:
        image_path = os.path.join(args.path, df.at[i, 'path'])
        array, dim_order = readers.read_array(image_path)

        if args.all_channel_pairs:
            n_channels = array.shape[dim_order.index('C')] if 'C' in dim_order else 1
            pairs = io_utils.channel_pairs(n_channels)
        else:
            pairs = [(args.channel1, args.channel2)]

        for c1, c2 in pairs:
            logging.info('Processing %s, channel pair (%d, %d)', df.at[i, 'path'], c1, c2)

            im1 = readers.select_channel(array, dim_order, c1)
            im2 = readers.select_channel(array, dim_order, c2)

            thr1 = get_threshold(im1, args.threshold_method)
            thr2 = get_threshold(im2, args.threshold_method)

            filename = f"{df.at[i, 'filename']}_c{c1}_c{c2}"
            m1, m2 = manders_coefficients(im1, im2, thr1, thr2, result_dir, filename)

            rows.append({
                'path': df.at[i, 'path'],
                'condition': df.at[i, 'condition'],
                'run': df.at[i, 'run'],
                'filename': df.at[i, 'filename'],
                'channel1': c1,
                'channel2': c2,
                'c1_thr': thr1,
                'c2_thr': thr2,
                'M1': m1,
                'M2': m2,
            })

    stats = pd.DataFrame(rows)
    stats.to_csv(os.path.join(result_dir, 'stats.csv'))
    plot_and_save_manders(stats, result_dir, args.color1, args.color2)
