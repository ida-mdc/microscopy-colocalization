"""Eager, metadata-light multi-format image reading.

Three backends dispatched by file extension, each returning the full pixel array plus a
dim-order string (e.g. "CYX", "TCZYX") describing its axes. ``select_channel`` then slices
out one channel regardless of which backend produced the array, so callers never need to
know the source format.

Modeled on pixel-patrol-loader-bio's loader plugins, trimmed to eager numpy arrays with no
lazy/dask loading and no metadata extraction beyond the dim order.
"""
import logging
import re
from pathlib import Path

import h5py
import numpy as np
import tifffile as tif

_TIFF_EXTENSIONS = {'.tif', '.tiff'}
_H5_EXTENSIONS = {'.h5', '.hdf5', '.ims'}

# Extensions scanned by default when a command isn't told which one to look for: the
# formats actually covered by the three backends + bioio plugins declared in pyproject.toml.
SUPPORTED_EXTENSIONS = sorted(
    {e.lstrip('.') for e in _TIFF_EXTENSIONS | _H5_EXTENSIONS} |
    {'czi', 'nd2', 'lif', 'png', 'jpg', 'jpeg'}
)

_AXIS_ATTR_KEYS = ('dim_order', '_ARRAY_DIMENSIONS', 'axes')

_IMARIS_DATASET = 'DataSet'
_IMARIS_LEVEL = 'ResolutionLevel 0'
_IMARIS_DATA = 'Data'
_IMARIS_TIMEPOINT_RE = re.compile(r'^TimePoint (\d+)$')
_IMARIS_CHANNEL_RE = re.compile(r'^Channel (\d+)$')
_IMARIS_DIM_ORDER = 'TCZYX'


def read_array(path):
    """Read an image file, returning (array, dim_order)."""
    ext = Path(path).suffix.lower()
    if ext in _TIFF_EXTENSIONS:
        array, dim_order = _read_tiff(path)
    elif ext in _H5_EXTENSIONS:
        array, dim_order = _read_h5(path)
    else:
        array, dim_order = _read_bioio(path)
    return _prefer_sample_axis_as_channel(array, dim_order)


def _prefer_sample_axis_as_channel(array, dim_order):
    """Both tifffile and bioio report an ambiguous/color-sample axis as 'S' (samples)
    rather than 'C' when there's no real per-biological-channel axis (e.g. plain tiff
    planes with no OME/ImageJ metadata, or RGB png/jpg). Treat 'S' as the channel axis
    whenever there's no meaningfully-sized 'C' axis to prefer instead.
    """
    if 'S' not in dim_order or array.shape[dim_order.index('S')] <= 1:
        return array, dim_order

    if 'C' in dim_order and array.shape[dim_order.index('C')] > 1:
        return array, dim_order  # a real multi-channel axis already exists; leave S alone

    if 'C' in dim_order:
        c_axis = dim_order.index('C')
        array = np.take(array, 0, axis=c_axis)
        dim_order = dim_order[:c_axis] + dim_order[c_axis + 1:]

    s_axis = dim_order.index('S')
    dim_order = dim_order[:s_axis] + 'C' + dim_order[s_axis + 1:]
    return array, dim_order


def select_channel(array, dim_order, channel_index):
    """Slice out one channel, given the array's dim-order string (e.g. "CYX", "TCZYX").

    If there is no 'C' axis, the array is returned unchanged (channel_index is ignored).
    Any 'T' axis is collapsed to its first timepoint.
    """
    if 'T' in dim_order:
        t_axis = dim_order.index('T')
        array = np.take(array, 0, axis=t_axis)
        dim_order = dim_order[:t_axis] + dim_order[t_axis + 1:]

    if 'C' not in dim_order:
        if channel_index is not None:
            logging.warning('No channel axis found in image with dim order %s; '
                             'channel_index=%s ignored.', dim_order, channel_index)
        return array

    c_axis = dim_order.index('C')
    if channel_index is None:
        raise ValueError(f'Image has a channel axis (dim order {dim_order}) but no '
                          f'channel_index was given.')
    return np.take(array, channel_index, axis=c_axis)


def count_channels(path):
    """Number of channels in the image at path, or 1 if it has no channel axis."""
    array, dim_order = read_array(path)
    if 'C' not in dim_order:
        return 1
    return array.shape[dim_order.index('C')]


# ---------------------------------------------------------------------------
# tifffile backend
# ---------------------------------------------------------------------------

def _read_tiff(path):
    with tif.TiffFile(path) as tf:
        if not tf.series:
            raise ValueError(f'No series found in TIFF file: {path}')
        series = tf.series[0]
        axes = (getattr(series, 'axes', None) or _default_dim_order(series.ndim)).upper()
        return series.asarray(), axes


# ---------------------------------------------------------------------------
# bioio backend (czi, nd2, lif, png/jpg, and anything else bioio supports)
# ---------------------------------------------------------------------------

def _read_bioio(path):
    from bioio import BioImage

    img = BioImage(path)
    dim_order = ''.join(img.dims.order)
    return np.asarray(img.data), dim_order


# ---------------------------------------------------------------------------
# h5 / hdf5 / .ims backend
# ---------------------------------------------------------------------------

def _open_h5(path):
    try:
        return h5py.File(str(path), 'r', locking=False)
    except TypeError:
        return h5py.File(str(path), 'r')


def _read_h5(path):
    with _open_h5(path) as h5:
        if _is_imaris_file(h5):
            return _read_imaris(h5)
        return _read_plain_h5(h5, path)


def _is_imaris_file(h5):
    marker = h5.attrs.get('ImarisDataSet')
    marker = marker.decode() if isinstance(marker, bytes) else marker
    return marker == 'ImarisDataSet' and _IMARIS_DATASET in h5


def _numbered_children(group, pattern):
    found = []
    for name in group.keys():
        match = pattern.match(name)
        if match:
            found.append((int(match.group(1)), name))
    return sorted(found)


def _read_imaris(h5):
    level_path = f'{_IMARIS_DATASET}/{_IMARIS_LEVEL}'
    if level_path not in h5:
        raise ValueError('Imaris .ims file has no ResolutionLevel 0')
    level = h5[level_path]

    timepoints = _numbered_children(level, _IMARIS_TIMEPOINT_RE)
    if not timepoints:
        raise ValueError('Imaris .ims file has no time points at ResolutionLevel 0')

    time_arrays = []
    for _, time_name in timepoints:
        channels = _numbered_children(level[time_name], _IMARIS_CHANNEL_RE)
        if not channels:
            raise ValueError(f"Imaris .ims time point '{time_name}' has no channels")
        channel_arrays = []
        for _, channel_name in channels:
            dataset_path = f'{level_path}/{time_name}/{channel_name}/{_IMARIS_DATA}'
            channel_arrays.append(h5[dataset_path][()])
        time_arrays.append(np.stack(channel_arrays, axis=0))

    return np.stack(time_arrays, axis=0), _IMARIS_DIM_ORDER


def _is_image_dataset(obj):
    return isinstance(obj, h5py.Dataset) and obj.ndim >= 2 and obj.dtype.kind in 'uif'


def _plain_dataset_paths(h5):
    paths = []
    h5.visititems(lambda name, obj: paths.append(name) if _is_image_dataset(obj) else None)
    return sorted(paths)


def _as_text(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    if isinstance(value, np.ndarray) and value.dtype.kind in 'SU':
        return ''.join(_as_text(v) if isinstance(v, bytes) else str(v) for v in value.flat)
    if isinstance(value, (str, list, tuple)):
        return value
    return None


def _axis_order_from_attrs(attrs, ndim):
    for key in _AXIS_ATTR_KEYS:
        value = _as_text(attrs.get(key))
        if value is None:
            continue
        letters = list(value) if isinstance(value, str) else [str(v) for v in value]
        if len(letters) == ndim and all(len(l) == 1 and l.isalpha() for l in letters):
            return ''.join(letters).upper()
    return None


def _default_dim_order(ndim):
    """Assume trailing YX, preceding axes get generic letters."""
    if ndim <= 2:
        return 'YX'[-ndim:] if ndim else ''
    import string
    return string.ascii_uppercase[:ndim - 2] + 'YX'


def _read_plain_h5(h5, path):
    paths = _plain_dataset_paths(h5)
    if not paths:
        raise ValueError(f'No image-like dataset found in HDF5 file: {path}')
    largest = max(paths, key=lambda p: h5[p].size * h5[p].dtype.itemsize)
    dset = h5[largest]
    dim_order = _axis_order_from_attrs(dset.attrs, dset.ndim) or _default_dim_order(dset.ndim)
    return dset[()], dim_order
