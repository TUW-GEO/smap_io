# -*- coding: utf-8 -*-

'''
Tests that use passed login information from travis CI to download a file
'''

import os
import tempfile

from smap_io.download import main
import unittest
import glob

class DownloadTest(unittest.TestCase):

    # these tsts only run of a username and pw are in the environment variables
    # can be set manually with export USERNAME="my_username" etc.
    @unittest.skipIf(
        "SMAPUSERNAME" not in os.environ or "SMAPPWD" not in os.environ,
        'Username and/or PW not found'
    )
    def test_full_download(self):

        dl_path = tempfile.mkdtemp()
        startdate = enddate = "2018-12-01"

        args = [
            dl_path, '-s', startdate, '-e', enddate,
            '--username', os.environ['SMAPUSERNAME'],
            '--password',  os.environ['SMAPPWD'],
            '--n_proc', '1'
        ]

        main(args)
        assert(os.listdir(dl_path) == ['2018.12.01'])
        files = glob.glob(os.path.join(dl_path, '2018.12.01', '*.h5'))
        assert len(files) == 1
