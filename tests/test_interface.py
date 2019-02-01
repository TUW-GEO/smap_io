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

from smap_io import SPL3SMP_Img
from smap_io import SPL3SMP_Ds
import os
from datetime import datetime


def test_SPL3SMP_Img():
    fname = os.path.join(os.path.dirname(__file__),
                         'smap_io-test-data', 'SPL3SMP', '2015.04.01',
                         'SMAP_L3_SM_P_20150401_R13080_001.h5')
    ds = SPL3SMP_Img(fname)
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
    assert sorted(metadata_keys) == sorted(
        list(image.metadata['soil_moisture'].keys()))


def test_SPL3SMP_Img_flatten():
    fname = os.path.join(os.path.dirname(__file__),
                         'smap_io-test-data', 'SPL3SMP', '2015.04.01',
                         'SMAP_L3_SM_P_20150401_R13080_001.h5')
    ds = SPL3SMP_Img(fname, flatten=True)
    image = ds.read()
    assert list(image.data.keys()) == ['soil_moisture']
    assert image.data['soil_moisture'].shape == (406 * 964,)
    # test for correct masking
    assert image.data['soil_moisture'][21 * 503] == -9999.
    metadata_keys = [u'_FillValue',
                     u'coordinates',
                     u'long_name',
                     u'valid_min',
                     u'units',
                     u'valid_max']
    assert sorted(metadata_keys) == sorted(
        list(image.metadata['soil_moisture'].keys()))


def test_SPL3SMP_Ds_read_by_date():
    root_path = os.path.join(os.path.dirname(__file__),
                             'smap_io-test-data', 'SPL3SMP')
    ds = SPL3SMP_Ds(root_path, crid=13080)
    image = ds.read(datetime(2015, 4, 1))
    assert list(image.data.keys()) == ['soil_moisture']
    assert image.data['soil_moisture'].shape == (406, 964)
    # test for correct masking
    assert image.data['soil_moisture'][21, 503] == -9999.


def test_SPL3SMP_Ds_read_by_date_flatten():
    root_path = os.path.join(os.path.dirname(__file__),
                             'smap_io-test-data', 'SPL3SMP')
    ds = SPL3SMP_Ds(root_path, crid=13080, flatten=True)
    image = ds.read(datetime(2015, 4, 1))
    assert list(image.data.keys()) == ['soil_moisture']
    assert image.data['soil_moisture'].shape == (406 * 964,)
    # test for correct masking
    assert image.data['soil_moisture'][21 * 503] == -9999.


def test_SPL3SMP_Ds_iterator():
    root_path = os.path.join(os.path.dirname(__file__),
                             'smap_io-test-data', 'SPL3SMP')
    ds = SPL3SMP_Ds(root_path, crid=13080)
    read_img = 0
    for image in ds.iter_images(datetime(2015, 4, 1),
                                datetime(2015, 4, 2)):
        assert list(image.data.keys()) == ['soil_moisture']
        assert image.data['soil_moisture'].shape == (406, 964)
        # test for correct masking
        assert image.data['soil_moisture'][21, 503] == -9999.
        read_img = read_img + 1

    assert read_img == 2


if __name__ == '__main__':
    test_SPL3SMP_Img()