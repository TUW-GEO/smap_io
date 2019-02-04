Downloading products
====================

SMAP products can be downloaded via HTTPS. You have to register an account
with NASA's Earthdata portal. Instructions can be found `here
<https://wiki.earthdata.nasa.gov/display/EL/How+To+Register+With+Earthdata+Login>`_.

After that you can use the command line program ``smap_download`` and your username
and password to download data between 2 dates.

The following command would download all available h5 files of the latest SMAP SPL3SMP data into the folder
``~/workspace/smap_data``. For more options on other available parameters
run ``smap_download --help``.

.. code::

   mkdir ~/workspace/smap_data
   smap_download ~/workspace/smap_data  --username *name* --password *password*

