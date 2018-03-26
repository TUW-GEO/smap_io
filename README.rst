=======
smap_io
=======

.. image:: https://travis-ci.org/TUW-GEO/smap_io.svg?branch=master
    :target: https://travis-ci.org/TUW-GEO/smap_io

.. image:: https://coveralls.io/repos/github/TUW-GEO/smap_io/badge.svg?branch=master
   :target: https://coveralls.io/github/TUW-GEO/smap_io?branch=master

.. image:: https://badge.fury.io/py/smap_io.svg
    :target: http://badge.fury.io/py/smap_io

.. image:: https://readthedocs.org/projects/smap_io/badge/?version=latest
   :target: http://smap_io.readthedocs.org/

SMAP (Soil Moisture Active Passive) data readers.

Works great in combination with `pytesmo <https://github.com/TUW-GEO/pytesmo>`_.

Citation
========

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.596391.svg
   :target: https://doi.org/10.5281/zenodo.596391

If you use the software in a publication then please cite it using the Zenodo DOI.
Be aware that this badge links to the latest package version.

Please select your specific version at https://doi.org/10.5281/zenodo.596391 to get the DOI of that version.
You should normally always use the DOI for the specific version of your record in citations.
This is to ensure that other researchers can access the exact research artefact you used for reproducibility.

You can find additional information regarding DOI versioning at http://help.zenodo.org/#versioning

Installation
============

Setup of a complete environment with `conda
<http://conda.pydata.org/miniconda.html>`_ can be performed using the following
commands:

.. code-block:: shell

  conda create -q -n smap_io-environment -c conda-forge numpy h5py pyproj netcdf4=1.2.2 pyresample scipy pandas matplotlib
  source activate smap_io-environment
  pip install smap_io

Supported Products
==================

- `SPL3SMP <http://nsidc.org/data/SPL3SMP>`_: SMAP L3 Radiometer Global Daily 36 km EASE-Grid Soil Moisture

Contribute
==========

We are happy if you want to contribute. Please raise an issue explaining what
is missing or if you find a bug. We will also gladly accept pull requests
against our master branch for new features or bug fixes.

Development setup
-----------------

For Development we also recommend the ``conda`` environment from the
installation part.

Guidelines
----------

If you want to contribute please follow these steps:

- Fork the smap_io repository to your account
- make a new feature branch from the smap_io master branch
- Add your feature
- please include tests for your contributions in one of the test directories
  We use py.test so a simple function called test_my_feature is enough
- submit a pull request to our master branch



