# -*- coding: utf-8 -*-

'''
Tests that use passed login information from travis CI to download a few files
'''

import os
import glob
import tempfile

from smap_io.download import main
import unittest
import time

class DownloadTest(unittest.TestCase):

    @unittest.skipIf("TRAVIS" not in os.environ or os.environ["TRAVIS"] == "false", "This runs only on Travis CI")
    def test_full_download(self):

        dl_path = tempfile.mkdtemp()
        startdate = "2018-12-01"
        enddate = "2018-12-01"

        args = [dl_path, '-s', startdate, '-e', enddate, '--product', 'SPL3SMP.005', '--username', os.environ['USERNAME'], '--password',  os.environ['PWD']]

        main(args)
        time.sleep(50) #wait until download is finished, better solution?
        #assert(os.listdir(dl_path) == ['2018.12.01', '2018.12.02'])
        #assert(os.listdir(os.path.join(dl_path, '2018.12.01')) == ['SMAP_L3_SM_P_20181201_R16020_002.h5'])
        #assert(os.listdir(os.path.join(dl_path, '2018.12.02')) == ['SMAP_L3_SM_P_20181202_R16020_001.h5'])
