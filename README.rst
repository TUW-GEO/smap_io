=======
smap_io
=======

.. image:: https://travis-ci.org/TUW-GEO/smap_io.svg?branch=master
    :target: https://travis-ci.org/TUW-GEO/smap_io

.. image:: https://coveralls.io/repos/github/TUW-GEO/smap_io/badge.svg?branch=master
   :target: https://coveralls.io/github/TUW-GEO/smap_io?branch=master

.. image:: https://badge.fury.io/py/smap_io.svg
    :target: http://badge.fury.io/py/smap_io

.. image:: https://zenodo.org/badge/12761/TUW-GEO/smap_io.svg
   :target: https://zenodo.org/badge/latestdoi/12761/TUW-GEO/smap_io

SMAP (Soil Moisture Active Passive) data readers.

Works great in combination with `pytesmo <https://github.com/TUW-GEO/pytesmo>`_.

Installation
============

Setup of a complete environment with `conda
<http://conda.pydata.org/miniconda.html>`_ can be performed using the following
commands:

.. code-block:: shell

  conda create -q -n smap_io-environment -c conda-forge numpy h5py pyproj netcdf=1.2.2 pyresample scipy pandas matplotlib
  source activate smap_io-environment
  pip install smap_io

Supported Products
==================

- `SPL3SMP <http://nsidc.org/data/SPL3SMP>`_: SMAP L3 Radiometer Global Daily 36 km EASE-Grid Soil Moisture

Documentation
=============

|Documentation Status|

.. |Documentation Status| image:: https://readthedocs.org/projects/smap_io/badge/?version=latest
   :target: http://smap_io.readthedocs.org/

