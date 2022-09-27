# -*- coding: utf-8 -*-

'''
Tests that use passed login information from travis CI to download a file
'''

import os
import tempfile

from smap_io.download import main
import unittest
import glob
import pytest

# These variables must be set in the workflow environment, and are taken
# by GitHub from the repository secrets.
env_username = "SMAPUSERNAME"
env_pwd = "SMAPPWD"

runtest = False
if (env_username in os.environ) and (env_pwd in os.environ):
    if os.environ[env_username] and os.environ[env_pwd]:
        runtest = True

class DownloadTest(unittest.TestCase):

    # these tests only run if a username and pw are set in the environment
    # variables. To manually set them: `export USERNAME="my_username"` etc.
    @unittest.skipIf(
        not runtest,
        'Username and/or PW not found'
    )
    @pytest.mark.wget
    def test_full_download(self):

        dl_path = tempfile.mkdtemp()
        startdate = enddate = "2018-12-01"

        args = [
            dl_path, '-s', startdate, '-e', enddate,
            '--username', os.environ[env_username],
            '--password',  os.environ[env_pwd],
            '--n_proc', '1'
        ]

        main(args)
        assert(os.listdir(dl_path) == ['2018.12.01'])
        files = glob.glob(os.path.join(dl_path, '2018.12.01', '*.h5'))
        assert len(files) == 1
