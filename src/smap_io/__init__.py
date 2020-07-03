# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = 'unknown'
finally:
    del get_distribution, DistributionNotFound


import os

src_path = os.path.join(os.path.dirname(__file__), '..')

tests_path = os.path.join(src_path, '..', 'tests')
if not os.path.exists(tests_path):
    tests_path = 'unknown'

testdata_path = os.path.join(src_path, '..', 'tests', 'smap_io-test-data')
if not os.path.exists(testdata_path):
    testdata_path = 'unknown'

from smap_io.interface import SPL3SMP_Img, SPL3SMP_Ds, SMAPTs