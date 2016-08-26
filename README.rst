====
smap_io
====

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

  conda create -q -n smap_io-environment numpy h5py pyproj
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

Example
=======

`SPL3SMP <http://nsidc.org/data/SPL3SMP>`_
------------------------------------------

After downloading the data you will have a path with subpaths of the format
``YYYY.MM.DD``. Let's call this path ``root_path``. To read the data of a
certain date use the following code:

.. code-block:: python

   from smap_io import SPL3SMP_Ds
   root_path = os.path.join(os.path.dirname(__file__),
                            'test_data', 'SPL3SMP')
   ds = SPL3SMP_Ds(root_path)
   image = ds.read(datetime(2015, 4, 1))
   assert list(image.data.keys()) == ['soil_moisture']
   assert image.data['soil_moisture'].shape == (406, 964)

The returned image is of the type `pygeobase.Image
<http://pygeobase.readthedocs.io/en/latest/api/pygeobase.html#pygeobase.object_base.Image>`_.
Which is only a small wrapper around a dictionary of numpy arrays.

If you only have a single image you can also read the data directly

.. code-block:: python

   from smap_io import SPL3SMP_Img
   fname = os.path.join(os.path.dirname(__file__),
                        'test_data', 'SPL3SMP', '2015.04.01',
                        'SMAP_L3_SM_P_20150401_R13080_001.h5')
   ds = SPL3SMP_Img(fname)
   image = ds.read()
   assert list(image.data.keys()) == ['soil_moisture']
   assert image.data['soil_moisture'].shape == (406, 964)
