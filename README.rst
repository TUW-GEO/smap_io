=======
smap_io
=======

.. image:: https://github.com/TUW-GEO/smap_io/actions/workflows/ci.yml/badge.svg?branch=master
   :target: https://github.com/TUW-GEO/smap_io/actions

.. image:: https://coveralls.io/repos/github/TUW-GEO/smap_io/badge.svg?branch=master
   :target: https://coveralls.io/github/TUW-GEO/smap_io?branch=master

.. image:: https://badge.fury.io/py/smap-io.svg
    :target: http://badge.fury.io/py/smap-io

.. image:: https://readthedocs.org/projects/smap-io/badge/?version=latest
    :target: https://smap-io.readthedocs.io/en/latest/?badge=latest

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

  $ conda create -q -n smap_io -c conda-forge numpy h5py pyproj netcdf4 pyresample pandas
  $ source activate smap_io
  $ pip install smap_io

You can also install all needed (conda and pip) dependencies at once using the
following commands after cloning this repository. This is recommended for
developers of the package.

.. code-block:: shell

  $ git clone https://github.com/TUW-GEO/smap_io.git --recursive
  $ cd smap_io
  $ conda create -n smap_io python=3.6 # or any supported python version
  $ source activate smap_io
  $ conda update -f environment.yml
  $ python setup.py develop

Supported Products
==================

- `SPL3SMP <http://nsidc.org/data/SPL3SMP>`_: SMAP L3 Radiometer Global Daily 36 km EASE-Grid Soil Moisture

Additional products will we added when need arises, feel free to open an issue to
add a new data product or even better a pull request.

Contribute
==========

We are happy if you want to contribute. Please raise an issue explaining what
is missing or if you find a bug. We will also gladly accept pull requests
against our master branch for new features or bug fixes.


Guidelines
----------

If you want to contribute please follow these steps:

- Fork the smap_io repository to your account
- make a new feature branch from the smap_io master branch
- Add your feature
- please include tests for your contributions in one of the test directories
  We use py.test so a simple function called test_my_feature is enough
- submit a pull request to our master branch



