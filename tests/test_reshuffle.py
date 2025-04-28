# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2016, TU Wien
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
Test module for image to time series conversion.
'''

import os
import glob
import tempfile
import numpy as np
import numpy.testing as nptest

from smap_io.reshuffle import main
from smap_io.interface import SMAPTs, SMAPL3_V9Reader
import pytest

@pytest.mark.parametrize("only_land", [
    True, False
])
def test_reshuffle(only_land):

    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smap_io-test-data", "SPL3SMP.006")
    startdate = "2020-04-01"
    enddate = "2020-04-02"
    parameters = ["soil_moisture", "soil_moisture_error", 'tb_time_seconds']
    time_key = 'tb_time_seconds'
    bbox = ['-5', '52', '0', '57']
    kwargs = ["--crid", "16515", "--overpass", 'PM', "--var_overpass_str", 'False'] + ['--bbox', *bbox]

    with tempfile.TemporaryDirectory() as ts_path:
        args = [inpath, ts_path, startdate, enddate, time_key] + parameters + kwargs

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 3
        ds = SMAPTs(ts_path,  parameters=parameters,
                    ioclass_kws={'read_bulk': True, 'read_dates': False})
        ds = SMAPL3_V9Reader(ts_path, ioclass_kws={'read_bulk': True})
        loc = (-2.8, 55.4)
        ts = ds.read(*loc)
        assert ds.grid.gpi2cell(ds.grid.find_nearest_gpi(*loc)[0]) == 1289
        soil_moisture_values_should = np.array(
            [0.262245], dtype=np.float32)

        nptest.assert_almost_equal(ts['soil_moisture'].values,
                                   soil_moisture_values_should,
                                   decimal=6)
        ds.close()

@pytest.mark.parametrize("only_land", [
    True, False
])
def test_reshuffle_am(only_land):

    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smap_io-test-data", "SPL3SMP.006")
    startdate = "2020-04-01"
    enddate = "2020-04-02"
    parameters = ["soil_moisture", "soil_moisture_error", 'tb_time_seconds']
    time_key = 'tb_time_seconds'
    bbox = ['-5', '52', '0', '57']
    kwargs = ["--crid", "16515", "--overpass", 'AM', "--var_overpass_str", 'False'] + ['--bbox', *bbox]

    with tempfile.TemporaryDirectory() as ts_path:
        args = [inpath, ts_path, startdate, enddate, time_key] + parameters + kwargs

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 3
        ds = SMAPTs(ts_path,  parameters=parameters,
                    ioclass_kws={'read_bulk': True, 'read_dates': False})
        ds = SMAPL3_V9Reader(ts_path, ioclass_kws={'read_bulk': True})
        loc = (-2.8, 55.4)
        ts = ds.read(*loc)
        assert ds.grid.gpi2cell(ds.grid.find_nearest_gpi(*loc)[0]) == 1289
        soil_moisture_values_should = np.array(
            [0.25584206, 0.24683787], dtype=np.float32)

        nptest.assert_almost_equal(ts['soil_moisture'].values,
                                   soil_moisture_values_should,
                                   decimal=6)
        ds.close()

@pytest.mark.parametrize("only_land", [
    True, False
])
def test_reshuffle_both(only_land):

    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smap_io-test-data", "SPL3SMP.006")
    startdate = "2020-04-01"
    enddate = "2020-04-02"
    parameters = ["soil_moisture", "soil_moisture_error", 'tb_time_seconds']
    time_key = 'tb_time_seconds'
    bbox = ['-5', '52', '0', '57']
    kwargs = ["--crid", "16515", "--overpass", 'BOTH', "--var_overpass_str", 'True'] + ['--bbox', *bbox]

    with tempfile.TemporaryDirectory() as ts_path:
        args = [inpath, ts_path, startdate, enddate, time_key] + parameters + kwargs

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 3
        ds = SMAPTs(ts_path,  parameters=parameters,
                    ioclass_kws={'read_bulk': True, 'read_dates': False})
        ds = SMAPL3_V9Reader(ts_path, ioclass_kws={'read_bulk': True})
        loc = (-2.8, 55.4)
        ts = ds.read(*loc)
        assert ds.grid.gpi2cell(ds.grid.find_nearest_gpi(*loc)[0]) == 1289
        soil_moisture_values_should = np.array(
            [0.255842, 0.246838, 0.262245], dtype=np.float32)

        nptest.assert_almost_equal(ts['soil_moisture'].values,
                                   soil_moisture_values_should,
                                   decimal=6)
        ds.close()

@pytest.mark.parametrize("only_land", [
    True, False
])
def test_reshuffle_overpass_is_none(only_land):

    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smap_io-test-data", "SPL3SMP.006")
    startdate = "2020-04-01"
    enddate = "2020-04-02"
    parameters = ["soil_moisture", "soil_moisture_error", 'tb_time_seconds']
    time_key = 'tb_time_seconds'
    bbox = ['-5', '52', '0', '57']
    kwargs = ["--crid", "16515"] + ['--bbox', *bbox]

    with tempfile.TemporaryDirectory() as ts_path:
        args = [inpath, ts_path, startdate, enddate, time_key] + parameters + kwargs

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 3
        ds = SMAPTs(ts_path,  parameters=parameters,
                    ioclass_kws={'read_bulk': True, 'read_dates': False})
        ds = SMAPL3_V9Reader(ts_path, ioclass_kws={'read_bulk': True})
        loc = (-2.8, 55.4)
        ts = ds.read(*loc)
        assert ds.grid.gpi2cell(ds.grid.find_nearest_gpi(*loc)[0]) == 1289
        soil_moisture_values_should = np.array(
            [0.255842, 0.246838], dtype=np.float32)

        nptest.assert_almost_equal(ts['soil_moisture'].values,
                                   soil_moisture_values_should,
                                   decimal=6)
        ds.close()