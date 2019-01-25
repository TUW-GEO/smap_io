# The MIT License (MIT)
#
# Copyright (c) 2016,TU Wien
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
Module to read single SMAP L3 images and image stacks
'''

import os
from pygeobase.io_base import ImageBase, MultiTemporalImageBase
from pygeobase.object_base import Image
from pynetcf.time_series import GriddedNcOrthoMultiTs
import pygeogrids.netcdf as ncdf
import h5py
import numpy as np

from datetime import timedelta


class SPL3SMP_Img(ImageBase):
    """
    Class for reading one image of SMAP Level 3 version 5 Passive Soil Moisture

    Parameters
    ----------
    filename: string
        filename of the SMAP h5 file
    mode: string, optional
        mode of opening the file, only 'r' is implemented at the moment
    parameter : string or list, optional
        one or list of parameters found at http://nsidc.org/data/smap_io/spl3smp/data-fields
        Default : 'soil_moisture'
    overpass : str, optional
        Select 'AM' for the descending overpass or 'PM' for the ascending one.
        Dataset version must support multiple overpasses, else choose None
        Passing PM will result in reading variables called *name*_pm
        Passing AM will result in reading variables called *name*
    flatten: boolean, optional
        If true the read data will be returned as 1D arrays.
    """

    def __init__(self, filename, mode='r', parameter='soil_moisture',
                 overpass=None, flatten=False):
        super(SPL3SMP_Img, self).__init__(filename, mode=mode)

        if type(parameter) != list:
            parameter = [parameter]
        self.overpass = overpass
        self.parameters = parameter
        self.flatten = flatten

    def read(self, timestamp=None):

        return_img = {}
        metadata_img = {}

        try:
            ds = h5py.File(self.filename)
        except IOError as e:
            print(e)
            print(" ".join([self.filename, "can not be opened"]))
            raise e

        overpass_str = '_' + self.overpass.upper() if self.overpass else ''

        sm_field = 'Soil_Moisture_Retrieval_Data%s' % overpass_str

        if sm_field not in ds.keys():
            raise NameError(sm_field, 'Field does not exists. Try deactivating overpass')

        if self.overpass:
            overpass_str = '_' + self.overpass.lower() if self.overpass.upper() == 'PM' else ''
        else:
            overpass_str = ''

        latitude = ds[sm_field]['latitude%s' % overpass_str][:]
        longitude = ds[sm_field]['longitude%s' % overpass_str][:]

        for parameter in self.parameters:
            metadata = {}
            param = ds[sm_field][parameter + overpass_str]
            data = param[:]
            # mask according to valid_min, valid_max and _FillValue
            try:
                fill_value = param.attrs['_FillValue']
                valid_min = param.attrs['valid_min']
                valid_max = param.attrs['valid_max']
            except KeyError:
                pass

            # fill metadata dictionary with metadata from image
            for key in param.attrs:
                metadata[key] = param.attrs[key]

            data = np.where(np.logical_or(data < valid_min, data > valid_max),
                            fill_value,
                            data)
            return_img[parameter + overpass_str] = data
            metadata_img[parameter + overpass_str] = metadata

        if self.flatten:
            longitude = longitude.flatten()
            latitude = latitude.flatten()
            for param in self.parameters:
                return_img[param + overpass_str] = return_img[param + overpass_str].flatten()

        return Image(longitude,
                     latitude,
                     return_img,
                     metadata_img,
                     timestamp)

    def write(self, data):
        raise NotImplementedError()

    def flush(self):
        pass

    def close(self):
        pass


class SPL3SMP_Ds(MultiTemporalImageBase):
    """
    Class for reading a collection of SMAP Level 3 Passive Soil Moisture images.

    Parameters
    ----------
    data_path: string
        root path of the SMAP data files
    parameter : string or list, optional
        one or list of parameters found at http://nsidc.org/data/smap_io/spl3smp/data-fields
        Default : 'soil_moisture'
    overpass : str, optional
        Select 'AM' for the descending overpass or 'PM' for the ascending one.
        Dataset version must support multiple overpasses, else choose None
    subpath_templ : list, optional
        If the data is store in subpaths based on the date of the dataset then this list
        can be used to specify the paths. Every list element specifies one path level.
    crid : int, optional (default: None)
        Only read files with this specific Composite Release ID.
        See also https://nsidc.org/data/smap/data_versions#CRID
    flatten: boolean, optional
        If true the read data will be returned as 1D arrays.
    """

    def __init__(self, data_path, parameter='soil_moisture', overpass=None,
                 subpath_templ=['%Y.%m.%d'], crid=None, flatten=False):

        ioclass_kws = {'parameter': parameter,
                       'overpass': overpass,
                       'flatten': flatten}
        if crid is None:
            filename_templ = "SMAP_L3_SM_P_{datetime}_*.h5"
        else:
            filename_templ = "SMAP_L3_SM_P_{datetime}_R%i*.h5" % crid

        super(SPL3SMP_Ds, self).__init__(data_path, SPL3SMP_Img,
                                         fname_templ=filename_templ,
                                         datetime_format="%Y%m%d",
                                         subpath_templ=subpath_templ,
                                         exact_templ=False,
                                         ioclass_kws=ioclass_kws)

    def tstamps_for_daterange(self, start_date, end_date):
        """
        return timestamps for daterange,

        Parameters
        ----------
        start_date: datetime
            start of date range
        end_date: datetime
            end of date range

        Returns
        -------
        timestamps : list
            list of datetime objects of each available image between
            start_date and end_date
        """
        timestamps = []
        diff = end_date - start_date
        for i in range(diff.days + 1):
            daily_date = start_date + timedelta(days=i)
            timestamps.append(daily_date)

        return timestamps



class SMAPTs(GriddedNcOrthoMultiTs):

    def __init__(self, ts_path, grid_path=None, **kwargs):
        '''
        Class for reading SMAP time series after reshuffling.

        Parameters
        ----------
        ts_path : str
            Directory where the netcdf time series files are stored
        grid_path : str, optional (default: None)
            Path to grid file, that is used to organize the location of time
            series to read. If None is passed, grid.nc is searched for in the
            ts_path.

        Optional keyword arguments that are passed to the Gridded Base:
        ------------------------------------------------------------------------
            parameters : list, optional (default: None)
                Specific variable names to read, if None are selected, all are read.
            offsets : dict, optional (default:None)
                Offsets (values) that are added to the parameters (keys)
            scale_factors : dict, optional (default:None)
                Offset (value) that the parameters (key) is multiplied with
            ioclass_kws: dict, (optional)
                Optional keyword arguments to pass to OrthoMultiTs class:
                ----------------------------------------------------------------
                    read_bulk : boolean, optional (default:False)
                        if set to True the data of all locations is read into memory,
                        and subsequent calls to read_ts read from the cache and
                        not from disk this makes reading complete files faster
                    read_dates : boolean, optional (default:False)
                        if false dates will not be read automatically but only on
                        specific request useable for bulk reading because currently
                        the netCDF num2date routine is very slow for big datasets.
        '''

        if grid_path is None:
            grid_path = os.path.join(ts_path, "grid.nc")

        grid = ncdf.load_grid(grid_path)
        super(SMAPTs, self).__init__(ts_path, grid, **kwargs)





