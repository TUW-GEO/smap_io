Downloading products
====================

SMAP products can be downloaded via HTTPS. You have to register an account
with NASA's Earthdata portal: https://urs.earthdata.nasa.gov/

After that you can use the command line program ``smap_download`` and your username
and password to download data between 2 dates.

In order for the download to work, the program line command "wget" must be
installed. On Linux this is usually the case. You test this by running.

.. code::

    $ wget -V

On Windows, running "wget -V" in the command line will usually return an error
like this

.. code::

    C:\Users>wget -V
    'wget' is not recognized as an internal or external command,
    operable program or batch file.

In that case you need to install `wget` first. There are many tutorials
available online. e.g. :

 - https://builtvisible.com/download-your-website-with-wget/
 - https://www.jcchouinard.com/wget/#Download_Wget_on_Windows

In short, you need to downloaded "wget.exe" into a location where Windows
command line can find it (specified in
your "PATH" environment variable; on Windows command simply run 'path' to
show all included directories). You can also add another directory to your
Windows PATH as described for example
`here <https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/>`_.
Then the command ``wget -V`` should also work
on windows (the download module of `smap_io` will use this function).

To test it you can run the following example.
This would download all available h5 files of the latest SMAP SPL3SMP data into the folder
``~/workspace/smap_data``. For more options on other available parameters
run ``smap_download --help``.

.. code::

   mkdir ~/workspace/smap_data
   smap_download ~/workspace/smap_data  --username *name* --password *password*

