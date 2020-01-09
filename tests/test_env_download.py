# -*- coding: utf-8 -*-

'''
Tests that use passed login information from travis CI to download a few files
'''

import os
import tempfile

from smap_io.download import main
import unittest

class DownloadTest(unittest.TestCase):

    # these tsts only run of a username and pw are in the environment variables
    # can be set manually with export USERNAME="my_username" etc.
    @unittest.skipIf("SMAPUSERNAME" not in os.environ or "SMAPPWD" not in os.environ, 'Username and/or PW not found')
    def test_full_download(self):

        dl_path = tempfile.mkdtemp()
        startdate = enddate = "2018-12-01"

        args = [dl_path, '-s', startdate, '-e', enddate, '--product', 'SPL3SMP.006',
                '--username', os.environ['SMAPUSERNAME'], '--password',  os.environ['SMAPPWD']]

        main(args)
        assert(os.listdir(dl_path) == ['2018.12.01'])
        assert(os.listdir(os.path.join(dl_path, '2018.12.01')) == ['SMAP_L3_SM_P_20181201_R16510_001.h5'])
