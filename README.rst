====
smap
====

.. image:: https://travis-ci.org/TUW-GEO/smap.svg?branch=master
    :target: https://travis-ci.org/TUW-GEO/smap

.. image:: https://coveralls.io/repos/github/TUW-GEO/smap/badge.svg?branch=master
   :target: https://coveralls.io/github/TUW-GEO/smap?branch=master

.. image:: https://badge.fury.io/py/smap.svg
    :target: http://badge.fury.io/py/smap

.. image:: https://zenodo.org/badge/12761/TUW-GEO/smap.svg
   :target: https://zenodo.org/badge/latestdoi/12761/TUW-GEO/smap

SMAP (Soil Moisture Active Passive) data readers.

Works great in combination with `pytesmo <https://github.com/TUW-GEO/pytesmo>`_.

Installation
============

Setup of a complete environment with `conda
<http://conda.pydata.org/miniconda.html>`_ can be performed using the following
commands:

.. code-block:: shell

  conda create -q -n smap-environment numpy h5py pyproj
  source activate smap-environment
  pip install smap

Supported Products
==================

- SPL3SMP: SMAP L3 Radiometer Global Daily 36 km EASE-Grid Soil Moisture

Documentation
=============

|Documentation Status|

.. |Documentation Status| image:: https://readthedocs.org/projects/smap/badge/?version=latest
   :target: http://smap.readthedocs.org/
