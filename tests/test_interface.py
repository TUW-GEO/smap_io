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
# The above copyright notice and this permission notice shall be included in all
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
    np.testing.assert_almost_equal(image.data['soil_moisture'][_id], 0.059678, 5)


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

    ds = SPL3SMP_Img(fname, flatten=False, overpass='PM', var_overpass_str=True,
                     grid=EASE36CellGrid(bbox=(lon-0.5, lat-0.5, lon+0.5, lat+0.5)))
    image_small = ds.read()
    np.testing.assert_almost_equal(image_small['soil_moisture_pm'][1,1], ref_sm, 5)

def test_SPL3SMP_Ds_read_by_date():
    root_path = os.path.join(os.path.dirname(__file__),
                             'smap_io-test-data', 'SPL3SMP.006')
    ds = SPL3SMP_Ds(root_path, crid=16515, overpass='AM', var_overpass_str=False)
    image = ds.read(datetime(2020, 4, 1))
    assert list(image.data.keys()) == ['soil_moisture']
    assert image.data['soil_moisture'].shape == (406, 964)
    # test for correct masking
    assert image.data['soil_moisture'][21, 503] == -9999.
    np.testing.assert_almost_equal(image.data['soil_moisture'][76, 466],
                                   0.281782, 5)

    ds = SPL3SMP_Ds(root_path, crid=16515, overpass='PM', var_overpass_str=True,
                    flatten=True)
    image = ds.read(datetime(2020, 4, 1))
    np.testing.assert_almost_equal(image.data['soil_moisture_pm'][idx2d_to_1d((76,466))],
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


if __name__ == '__main__':
    test_SPL3SMP_Ds_iterator()
