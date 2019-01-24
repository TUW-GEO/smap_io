.. include:: ../README.rst

Downloading products
====================

SMAP products can be downloaded via HTTPS. You have to register an account
with NASA's Earthdata portal. Instructions can be found `here
<https://wiki.earthdata.nasa.gov/display/EL/How+To+Register+With+Earthdata+Login>`_.

After that you can use the command line program ``smap_download``.

.. code::

   mkdir ~/workspace/smap_data
   smap_download ~/workspace/smap_data  --username *name* --password *password*

would download all available h5 files of the latest SMAP SPL3SMP data into the folder
``~/workspace/smap_data``. For more options run ``smap_download -h``.

Reading images
==============

`SPL3SMP <http://nsidc.org/data/SPL3SMP>`_
------------------------------------------

After downloading the data you will have a path with subpaths of the format
``YYYY.MM.DD``. Let's call this path ``root_path``. To read 'soil_moisture'
data for the descending overpass of a certain date use the following code:

.. code-block:: python

   from smap_io import SPL3SMP_Ds
   root_path = os.path.join(os.path.dirname(__file__),
                            'test_data', 'SPL3SMP')
   ds = SPL3SMP_Ds(root_path, overpass='AM')
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
   ds = SPL3SMP_Img(fname, overpass='PM')
   image = ds.read()
   assert list(image.data.keys()) == ['soil_moisture']
   assert image.data['soil_moisture_pm'].shape == (406, 964)

Conversion to time series format
================================

For a lot of applications it is favorable to convert the image based format into
a format which is optimized for fast time series retrieval. This is what we
often need for e.g. validation studies. This can be done by stacking the images
into a netCDF file and choosing the correct chunk sizes or a lot of other
methods. We have chosen to do it in the following way:

- Store the grid points in a 1D array. This also allows reduction of the data
  volume by e.g. only saving the points over land.
- Store the time series in netCDF4 in the Climate and Forecast convention
  `Orthogonal multidimensional array representation
  <http://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#_orthogonal_multidimensional_array_representation>`_
- Store the time series in 5x5 degree cells. This means there will be 2566 cell
  files and a file called ``grid.nc`` which contains the information about which
  grid point is stored in which file. This allows us to read a whole 5x5 degree
  area into memory and iterate over the time series quickly.

  .. image:: 5x5_cell_partitioning.png
     :target: _images/5x5_cell_partitioning.png

`SPL3SMP <http://nsidc.org/data/SPL3SMP>`_
------------------------------------------

This conversion can be performed using the ``smap_repurpose`` command line
program. An example would be:

.. code-block:: shell

   smap_repurpose /SPL3SMP_data /timeseries/data 2015-04-01 2015-04-02 soil_moisture soil_moisture_error --overpass AM

Which would take SMAP SPL3SMP data stored in ``/SPL3SMP_data`` from April 1st
2015 to April 2nd 2015 and store the parameters ``soil_moisture`` and
``soil_moisture_error`` for the ``AM`` overpass as time series in the
folder ``/timeseries/data``. When the ``PM`` overpass is selected, time series variables
will be renamed with the suffix *_pm*.

Conversion to time series is performed by the `repurpose package
<https://github.com/TUW-GEO/repurpose>`_ in the background. For custom settings
or other options see the `repurpose documentation
<http://repurpose.readthedocs.io/en/latest/>`_ and the code in
``smap_io.reshuffle``.

Reading converted time series data
----------------------------------

For reading the data the ``smap_repurpose`` command produces the class
``SMAPTs`` can be used. Bulk reading speeds up reading multiple points from
a cell file by storing the file in memory for subsequent calls (when reading a single point,
this is option is slower).

.. code-block:: python

    from smap_io.interface import SMAPTs
    ds = SMAPTs(ts_path, parameters=['soil_moisture','soil_moisture_error'],
                ioclass_kws={'read_bulk': True, 'read_dates': False})
    # read_ts takes either lon, lat coordinates or a grid point indices.
    # and returns a pandas.DataFrame
    ts = ds.read_ts(45, 15) # (lon, lat)


Contents
========

.. toctree::
   :maxdepth: 2

   License <license>
   Authors <authors>
   Changelog <changes>
   Module Reference <api/modules>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`