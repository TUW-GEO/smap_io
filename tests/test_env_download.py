# -*- coding: utf-8 -*-

'''
Tests that use passed login information from travis CI to download a few files
'''

import os

def test_environment_var():
    assert os.environ["TESTVAR"] == 'test'
