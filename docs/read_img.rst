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
