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
from smap_io.interface import SMAPTs


def test_reshuffle():

    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smap_io-test-data", "SPL3SMP")
    ts_path = tempfile.mkdtemp()
    startdate = "2015-04-01"
    enddate = "2015-04-02"
    parameters = ["soil_moisture", "soil_moisture_error"]
    crid = ["--crid", "13080"]

    args = [inpath, ts_path, startdate, enddate] + parameters + crid
    main(args)
    assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 2449
    ds = SMAPTs(ts_path,  parameters=['soil_moisture','soil_moisture_error'],
                ioclass_kws={'read_bulk': True, 'read_dates': False})
    ts = ds.read_ts(-2.8, 55.4)
    ds.grid.arrcell[35 * 964 + 474] == 1289
    soil_moisture_values_should = np.array(
        [0.267108, 0.275263], dtype=np.float32)

    nptest.assert_almost_equal(ts['soil_moisture'].values,
                               soil_moisture_values_should,
                               decimal=6)