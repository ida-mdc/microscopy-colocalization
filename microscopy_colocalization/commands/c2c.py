"""c2c: channel-to-channel colocalization (Manders' overlap coefficients), from
channel_colocalization/colocalization.py, migrated onto the shared multi-format reader.
Logic changes from the original: args.channels replaces the hardcoded channel-2 index (which
silently ignored the --channel2/-c2i flag) and the separate --all-channel-pairs flag (2
channels given -> one pair, same as before; 3+ -> every pair, automatically).
"""
import logging
import os

import numpy as np
import pandas as pd
import tifffile as tif

from microscopy_colocalization import io_utils, readers
from microscopy_colocalization.colors import channel_color
from microscopy_colocalization.plotting import plot_and_save_manders
from microscopy_colocalization.threshold import THRESHOLD_METHODS, get_threshold


def add_arguments(parser):
    parser.description = (
        "Channel-to-channel colocalization: threshold two or more channels of the same "
        "multi-channel image and report Manders' M1/M2 overlap coefficients for every pair."
    )
    parser.add_argument('-p', '--path', required=True,
                         help='Root folder of images, laid out as condition/file or '
                              'condition/run/file (one or more conditions, each a subfolder).')
    parser.add_argument('-ext', '--extension', default=None,
                         help='Image file extension to look for, e.g. tif, czi, ims (no dot). '
                              'If omitted, scans for every supported format '
                              f'({", ".join(readers.SUPPORTED_EXTENSIONS)}).')
    parser.add_argument('-c', '--channels', action='append', type=int,
                         help='Index of a channel to compare, 0 means the first channel in '
                              'the file. Give at least twice, e.g. -c 0 -c 1. With more than '
                              'two, every unique pair is compared.')
    parser.add_argument('--colormap', default=None,
                         help='Matplotlib colormap name; each channel index gets one color '
                              'from it, consistent across every plot. Default is a small '
                              'built-in palette of microscopy-overlay-style colors.')
    parser.add_argument('-tm', '--threshold_method', default='otsu', choices=THRESHOLD_METHODS,
                         help='Method used to separate signal from background in each channel '
                              '(default: otsu).')
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


def run(args):
    io_utils.require_min_items(args._parser, 'channels', args.channels)

    result_dir = io_utils.create_result_dir(args.path, prefix='c2c')
    io_utils.set_logger(result_dir)
    io_utils.save_args_to_file(args, result_dir)

    paths = io_utils.get_all_image_paths(args.path, args.extension)
    df = io_utils.paths_to_df(paths)
    pairs = io_utils.all_pairs(args.channels)

    rows = []
    for i in df.index:
        image_path = os.path.join(args.path, df.at[i, 'path'])
        array, dim_order = readers.read_array(image_path)

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

    for (c1, c2), pair_stats in stats.groupby(['channel1', 'channel2']):
        plot_and_save_manders(pair_stats, result_dir,
                               channel_color(c1, args.colormap), channel_color(c2, args.colormap),
                               pair_tag=f'c{c1}_c{c2}')
