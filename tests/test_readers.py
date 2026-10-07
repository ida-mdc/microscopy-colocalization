import h5py
import imageio.v3 as iio
import numpy as np
import pytest
import tifffile as tif

from microscopy_colocalization import readers


def test_tif_without_metadata_promotes_sample_axis_to_channel(tmp_path):
    """A plain multi-page tif has no OME/ImageJ channel metadata, so tifffile reports the
    extra axis as 'S' (samples); it must still be usable as the channel axis.
    """
    path = tmp_path / 'img.tif'
    arr = np.stack([np.full((8, 8), v, dtype=np.uint16) for v in (10, 20, 30)])
    tif.imwrite(path, arr, photometric='minisblack')

    array, dim_order = readers.read_array(str(path))
    assert 'C' in dim_order
    assert readers.select_channel(array, dim_order, 1).flat[0] == 20


def test_plain_h5_reads_declared_axis_order(tmp_path):
    path = tmp_path / 'img.h5'
    arr = np.stack([np.full((8, 8), v, dtype=np.float32) for v in (1, 2, 3)])
    with h5py.File(path, 'w') as f:
        dset = f.create_dataset('data', data=arr)
        dset.attrs['dim_order'] = 'CYX'

    array, dim_order = readers.read_array(str(path))
    assert dim_order == 'CYX'
    assert readers.select_channel(array, dim_order, 2).flat[0] == 3


def test_imaris_like_h5_assembles_channels_from_nested_groups(tmp_path):
    path = tmp_path / 'img.ims'
    with h5py.File(path, 'w') as f:
        f.attrs['ImarisDataSet'] = 'ImarisDataSet'
        for c, value in enumerate((7, 9)):
            grp = f.create_group(f'DataSet/ResolutionLevel 0/TimePoint 0/Channel {c}')
            grp.create_dataset('Data', data=np.full((2, 4, 4), value, dtype=np.uint16))

    array, dim_order = readers.read_array(str(path))
    assert dim_order == 'TCZYX'
    assert readers.select_channel(array, dim_order, 0).flat[0] == 7
    assert readers.select_channel(array, dim_order, 1).flat[0] == 9


def test_select_channel_ignores_missing_channel_axis_with_warning(caplog):
    array = np.zeros((8, 8))
    with caplog.at_level('WARNING'):
        result = readers.select_channel(array, 'YX', channel_index=0)
    assert result.shape == (8, 8)
    assert caplog.records


def test_select_channel_requires_index_when_channel_axis_present():
    array = np.zeros((2, 8, 8))
    with pytest.raises(ValueError):
        readers.select_channel(array, 'CYX', channel_index=None)


def test_bioio_backend_reads_png_color_channels(tmp_path):
    path = tmp_path / 'img.png'
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rgb[..., 0] = 10
    rgb[..., 1] = 20
    rgb[..., 2] = 30
    iio.imwrite(path, rgb)

    array, dim_order = readers.read_array(str(path))
    assert 'C' in dim_order
    assert readers.select_channel(array, dim_order, 0).flat[0] == 10
    assert readers.select_channel(array, dim_order, 1).flat[0] == 20
    assert readers.select_channel(array, dim_order, 2).flat[0] == 30


def test_select_channel_collapses_time_axis_to_first_timepoint():
    array = np.arange(2 * 3 * 4 * 4).reshape(2, 3, 4, 4)  # TCYX
    result = readers.select_channel(array, 'TCYX', channel_index=1)
    expected = array[0, 1]
    assert np.array_equal(result, expected)
