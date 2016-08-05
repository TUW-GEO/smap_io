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

'''

from pygeobase.io_base import ImageBase, MultiTemporalImageBase
from pygeobase.object_base import Image
import h5py
import numpy as np

from datetime import timedelta


class SPL3SMP_Img(ImageBase):
    """
    Class for reading one image of SMAP Level 3 Passive Soil Moisture

    Parameters
    ----------
    filename: string
        filename of the GLDAS grib file
    mode: string, optional
        mode of opening the file, only 'r' is implemented at the moment
    parameter : string or list, optional
        one or list of parameters found at http://nsidc.org/data/smap/spl3smp/data-fields
        Default : 'soil_moisture'
    """

    def __init__(self, filename, mode='r', parameter='soil_moisture'):
        super(SPL3SMP_Img, self).__init__(filename, mode=mode)

        if type(parameter) != list:
            parameter = [parameter]
        self.parameters = parameter

    def read(self, timestamp=None):

        return_img = {}

        try:
            ds = h5py.File(self.filename)
        except IOError as e:
            print(e)
            print(" ".join([self.filename, "can not be opened"]))
            raise e

        latitude = ds['Soil_Moisture_Retrieval_Data']['latitude'][:]
        longitude = ds['Soil_Moisture_Retrieval_Data']['longitude'][:]

        for parameter in self.parameters:
            param = ds['Soil_Moisture_Retrieval_Data'][parameter]
            data = param[:]
            # mask according to valid_min, valid_max and _FillValue
            try:
                fill_value = param.attrs['_FillValue']
                valid_min = param.attrs['valid_min']
                valid_max = param.attrs['valid_max']
            except KeyError:
                pass

            data = np.where(np.logical_or(data < valid_min, data > valid_max),
                            fill_value,
                            data)
            return_img[parameter] = data

        return Image(longitude,
                     latitude,
                     return_img,
                     {},
                     timestamp)

    def write(self, data):
        raise NotImplementedError()

    def flush(self):
        pass

    def close(self):
        pass
