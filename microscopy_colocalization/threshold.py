"""Thresholding shared by c2c and p2c.

Unifies the previously-duplicated (and identical) otsu/li/triangle/yen threshold-value logic
from ida_tools.image_operations.get_threshold and fish_colocalization's inline version.
get_distance_map's "mask dominance" warning condition is inverted from the original (bug fix:
the original warned when background dominated, backwards from its own stated intent).
"""
import logging

import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.filters import threshold_li, threshold_otsu, threshold_triangle, threshold_yen

THRESHOLD_METHODS = ['otsu', 'li', 'triangle', 'yen']

_METHODS = {
    'otsu': threshold_otsu,
    'li': threshold_li,
    'triangle': threshold_triangle,
    'yen': threshold_yen,
}


def get_threshold(image, method='otsu'):
    """Calculate the threshold value of an image using the given method."""
    if method not in _METHODS:
        raise ValueError(f"Threshold method must be one of: {list(_METHODS)}")
    return _METHODS[method](image.flatten())


def get_distance_map(image, thr):
    """For every background (below-threshold) pixel, distance to the nearest foreground pixel."""
    mask = image > thr
    if np.sum(mask) > mask.size // 2:
        logging.warning('Threshold mask has more foreground than background pixels. '
                         'Please check that thresholding did not invert object/background.')
    return distance_transform_edt(~mask)
