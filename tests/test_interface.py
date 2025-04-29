# The MIT License (MIT)
#
# Copyright (c) 2016,TU Wien
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
Tests for reading the image datasets.
'''

from smap_io.interface import SPL3SMP_Img
from smap_io.interface import SPL3SMP_Ds
import os
from datetime import datetime
import numpy as np
from smap_io.grid import EASE36CellGrid
import pytest
import smap_io.interface as interface
from unittest.mock import patch, MagicMock
from smap_io.interface import SPL3SMP_Img
import pytest
from unittest.mock import MagicMock, patch
import h5py
glob_shape = (406, 964)


def idx2d_to_1d(idx_2d, shape=glob_shape, flip=True):
    if flip:
        return (shape[0] - (idx_2d[0] + 1)) * shape[1] + idx_2d[1]
    else:
        return idx_2d[0] * shape[1] + idx_2d[1]


def test_SPL3SMP_Img_land():
    fname = os.path.join(os.path.dirname(__file__),
                         'smap_io-test-data', 'SPL3SMP.006', '2020.04.02',
                         'SMAP_L3_SM_P_20200402_R16515_001.h5')
    grid = EASE36CellGrid(bbox=(112, -37, 130, -11), only_land=True)
    ds = SPL3SMP_Img(fname, grid=grid, overpass='PM', var_overpass_str=False,
                     flatten=True)
    image = ds.read()
    assert list(image.data.keys()) == ['soil_moisture']
    assert image.data['soil_moisture'].shape == (2090,)
    # test for correct masking
    assert image.data['soil_moisture'][0] == -9999.
    gpi, _ = grid.find_nearest_gpi(124.903, -32.311)
    _id = np.where(grid.activegpis == gpi)[0]
    np.testing.assert_almost_equal(image.data['soil_moisture'][_id], 0.059678,
                                   5)


def test_SPL3SMP_Img():
    fname = os.path.join(os.path.dirname(__file__),
                         'smap_io-test-data', 'SPL3SMP.006', '2020.04.01',
                         'SMAP_L3_SM_P_20200401_R16515_001.h5')
    ds = SPL3SMP_Img(fname, overpass='PM', var_overpass_str=False)
    image = ds.read()
    assert list(image.data.keys()) == ['soil_moisture']
    assert image.data['soil_moisture'].shape == (406, 964)
    # test for correct masking
    assert image.data['soil_moisture'][21, 503] == -9999.
    metadata_keys = [u'_FillValue',
                     u'coordinates',
                     u'long_name',
                     u'valid_min',
                     u'units',
                     u'valid_max']
    np.testing.assert_almost_equal(image.data['soil_moisture'][76, 466],
                                   0.258598, 5)
    assert sorted(metadata_keys) == sorted(
        list(image.metadata['soil_moisture'].keys()))


def test_SPL3SMP_Img_flatten():
    fname = os.path.join(os.path.dirname(__file__),
                         'smap_io-test-data', 'SPL3SMP.006', '2020.04.01',
                         'SMAP_L3_SM_P_20200401_R16515_001.h5')
    ds = SPL3SMP_Img(fname, flatten=True, overpass='PM', var_overpass_str=True)
    image = ds.read()
    assert list(image.data.keys()) == ['soil_moisture_pm']
    assert image.data['soil_moisture_pm'].shape == (np.prod(glob_shape),)
    idx2d = (76, 466)
    idx1d = idx2d_to_1d(idx2d)
    ref_sm = 0.258598
    np.testing.assert_almost_equal(
        np.flipud(image.data['soil_moisture_pm'].reshape((406, 964)))[idx2d],
        ref_sm, 5
    )
    np.testing.assert_almost_equal(image.data['soil_moisture_pm'][idx1d],
                                   ref_sm, 5)

    lat = image.lat[idx1d]
    lon = image.lon[idx1d]

    # test for correct masking
    assert image.data['soil_moisture_pm'][21 * 503] == -9999.
    metadata_keys = [u'_FillValue',
                     u'coordinates',
                     u'long_name',
                     u'valid_min',
                     u'units',
                     u'valid_max']
    assert sorted(metadata_keys) == sorted(
        list(image.metadata['soil_moisture_pm'].keys()))

    ds = SPL3SMP_Img(fname, flatten=False, overpass='PM',
                     var_overpass_str=True,
                     grid=EASE36CellGrid(
                         bbox=(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5)))
    image_small = ds.read()
    np.testing.assert_almost_equal(image_small['soil_moisture_pm'][1, 1],
                                   ref_sm, 5)


def test_SPL3SMP_Ds_read_by_date():
    root_path = os.path.join(os.path.dirname(__file__),
                             'smap_io-test-data', 'SPL3SMP.006')
    ds = SPL3SMP_Ds(root_path, crid=16515, overpass='AM',
                    var_overpass_str=False)
    image = ds.read(datetime(2020, 4, 1))
    assert list(image.data.keys()) == ['soil_moisture']
    assert image.data['soil_moisture'].shape == (406, 964)
    # test for correct masking
    assert image.data['soil_moisture'][21, 503] == -9999.
    np.testing.assert_almost_equal(image.data['soil_moisture'][76, 466],
                                   0.281782, 5)

    ds = SPL3SMP_Ds(root_path, crid=16515, overpass='PM',
                    var_overpass_str=True,
                    flatten=True)
    image = ds.read(datetime(2020, 4, 1))
    np.testing.assert_almost_equal(
        image.data['soil_moisture_pm'][idx2d_to_1d((76, 466))],
        0.258598, 5)


def test_SPL3SMP_Ds_iterator():
    root_path = os.path.join(os.path.dirname(__file__),
                             'smap_io-test-data', 'SPL3SMP.006')
    ds = SPL3SMP_Ds(root_path, overpass='AM', var_overpass_str=False)
    read_img = 0
    for image in ds.iter_images(datetime(2020, 4, 1),
                                datetime(2020, 4, 2)):
        assert list(image.data.keys()) == ['soil_moisture']
        assert image.data['soil_moisture'].shape == (406, 964)
        # test for correct masking
        assert image.data['soil_moisture'][21, 503] == -9999.
        read_img = read_img + 1

    assert read_img == 2


def test_initial_overpass_state_AM_status():
    assert type(interface.overpass_state_AM) == bool
    assert interface.overpass_state_AM == True


def test_overpass_change():
    interface.overpass_change('overpass_state_AM')

    # Verify that the value in 'interface' has changed
    assert interface.overpass_state_AM is False

    # Call the function again to toggle it back
    interface.overpass_change('overpass_state_AM')

    # Verify that the value in 'interface' is toggled back to the original
    assert interface.overpass_state_AM is True

    # Test non-existent variable in 'interface'
    with pytest.raises(NameError):
        interface.overpass_change('non_existent_var')

def test_initial_counter_status():
    assert type(interface.counter) == int
    assert interface.counter == 0

def test_increment_counter():
    counter_before = interface.counter
    interface.increment_counter('counter')

    # Verify that the value in 'interface' has changed
    assert counter_before + 1 == interface.counter




def test_read_file_open_error():
    # Mock filename for the test
    invalid_filename = "invalid_file.h5"

    # Create an instance of SPL3SMP_Img with the mocked filename
    reader = SPL3SMP_Img(filename=invalid_filename, mode="r",
                         parameter="soil_moisture")

    # Mock h5py.File to simulate IOError when it tries to open the file
    with patch("h5py.File",
               side_effect=IOError("File cannot be opened")) as mock_h5py:
        # Assert that IOError is raised and caught properly
        with pytest.raises(IOError, match="File cannot be opened"):
            reader.read()

        # Ensure the mocked function (h5py.File) was called with the correct filename
        mock_h5py.assert_called_once_with(invalid_filename, mode="r")

def test_missing_sm_field():
    # Define a mocked 'sm_field' value
    fname = os.path.join(os.path.dirname(__file__),
                         'smap_io-test-data', 'SPL3SMP.006', '2020.04.02',
                         'SMAP_L3_SM_P_20200402_R16515_001.h5')
    grid = EASE36CellGrid(bbox=(112, -37, 130, -11), only_land=True)
    sm_field = "missing_field"

    # Create an instance of SPL3SMP_Img
    ds = SPL3SMP_Img(fname, grid=grid, overpass='PM', var_overpass_str=False,
                     flatten=True)

    # Mock a dataset without the required field
    mock_ds = MagicMock()
    mock_ds.keys.return_value = ["another_field",
                                 "unrelated_field"]  # Doesn't contain 'sm_field'

    # Patch h5py.File to return the mock dataset
    with patch("h5py.File", return_value=mock_ds):
        # Ensure that a NameError is raised when accessing a missing field
        with pytest.raises(NameError,
                           match="Field does not exists. Try deactivating overpass option."):
            ds.read()





def test_overpass_is_None_error():
    """
    Test the behavior when there is only one overpass.
    """
    fname = os.path.join(os.path.dirname(__file__),
                         'smap_io-test-data', 'SPL3SMP.006', '2020.04.02',
                         'SMAP_L3_SM_P_20200402_R16515_001.h5')
    grid = EASE36CellGrid(bbox=(112, -37, 130, -11), only_land=True)

    # Create an instance of SPL3SMP_Img
    ds = SPL3SMP_Img(fname, grid=grid, overpass=None, var_overpass_str=False,
                     flatten=True)
    with pytest.raises(
            IOError) as excinfo:  # Context manager to capture the exception
            ds.read()

    # Assert the exception's message
    assert str(excinfo.value) == (
        "Multiple overpasses found in file, please specify one overpass "
        "to load: ['AM', 'PM']"
    )

if __name__ == '__main__':
    test_SPL3SMP_Ds_iterator()
