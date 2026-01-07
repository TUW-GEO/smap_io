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
# The above copyright notice and this permission notice shall be included in
# all
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

import pandas as pd
from pygeobase.io_base import ImageBase, MultiTemporalImageBase
from pygeobase.object_base import Image
from pygeogrids.netcdf import load_grid
from pynetcf.time_series import GriddedNcOrthoMultiTs
import pygeogrids.netcdf as ncdf
import h5py
from parse import *
from datetime import timedelta
import warnings
from smap_io.grid import EASE36CellGrid
from pynetcf.time_series import GriddedNcIndexedRaggedTs
import os
import re
import shutil
from datetime import datetime
import numpy as np
import xarray as xr
import logging



counter = 0

overpass_state_AM = True

def increment_counter(var_name):
    if var_name in globals():
        globals()[var_name] += 1



def overpass_change(var_name):
    if var_name in globals():
        globals()[var_name] = not globals()[var_name]
    else:
        raise NameError(f"Global variable '{var_name}' is not defined.")





class SPL3SMP_Img(ImageBase):
    """
    Class for reading one image of SMAP Level 3 version 5 Passive Soil Moisture

    Parameters
    ----------
    filename: str
        filename of the SMAP h5 file to read.
    mode: str, optional (default: 'r')
        mode of opening the file, only 'r' is implemented at the moment
    parameter : str or list, optional (default : 'soil_moisture')
        one or list of parameters found at
        http://nsidc.org/data/smap_io/spl3smp/data-fields
    overpass : str, optional (default: 'AM')
        Select 'AM' for the descending overpass or 'PM' for the ascending one.
        If there is only one overpass in the file (old SPL3 versions) pass
        None.
        Passing PM will result in reading variables called *name*_pm
        Passing AM will result in reading variables called *name*
    var_overpass_str : bool, optional (default: True)
        Append overpass indicator to the loaded variables. E.g. Soil Moisture
        will be called soil_moisture_pm and soil_moisture_am, and soil_moisture
        in all cases if this is set to False.
    grid: pygeogrids.CellGrid, optional (default: None)
        A (sub)grid of points to read. e.g. to read data for land points only
        for a specific bounding box. Must be a subgrid of an EASE25 Grid.
        If None is passed, all point are read.
    flatten: bool, optional (default: False)
        If true the read data will be returned as 1D arrays. Where the first
        value refers to the bottom-left most point in the grid!
        If not flattened, a 2d array where the min Lat is in the bottom row
        is returned!
    time_key: str, optional (default: 'tb_time_seconds')
        Defines the parameter in the input file to be used as time stamp.
        If the time_key is not None the output time_series will be in the
        GriddedNcContiguousRaggedTs displaying the observation time with
        seconds accuracy. If the time_key is None the output time_series will
        be in the GriddedNcOrthoMultiTs format.

    """

    def __init__(self,
                 filename,
                 mode='r',
                 parameter='soil_moisture',
                 overpass='AM',
                 time_key='tb_time_seconds',
                 var_overpass_str=True,
                 grid=None,
                 flatten=False):

        super().__init__(filename, mode=mode)
        self.grid = EASE36CellGrid() if grid is None else grid


        if type(parameter) != list:
            parameter = [parameter]

        self.overpass = overpass.upper() if overpass is not None else None
        self.overpass_templ = 'Soil_Moisture_Retrieval_Data{orbit}'
        self.var_overpass_str = var_overpass_str
        self.parameters = parameter
        self.flatten = flatten
        self.time_key = time_key

    def read(self, timestamp=None) -> Image:

        """
        Read a single h5 image file to pygeobase Image.

        Parameters
        ----------
        timestamp: datetime, optional (default: False)
            Time stamp to read. If None is passed, the Image will
            not have a time stamp assigned.
        """

        return_data = {}
        return_meta = {}

        try:
            ds = h5py.File(self.filename, mode='r')
        except IOError as e:
            print(e)
            print(" ".join([self.filename, "can not be opened"]))
            raise e

        if self.overpass is None:
            overpasses = []
            for k in list(ds.keys()):
                p = parse(self.overpass_templ, k)
                if p is not None and ('orbit' in p.named.keys()):
                    overpasses.append(p['orbit'][1:])  # omit leading _

            if len(overpasses) > 1:
                raise IOError(
                    'Multiple overpasses found in file, please specify '
                    f'one overpass to load: {overpasses}')
            else:
                self.overpass = overpasses[0].upper()

        else:
            assert self.overpass in ['AM', 'PM', 'BOTH']

        overpass = self.overpass
        if overpass == 'BOTH':
            if overpass_state_AM:
                op = 'AM'
            else:
                op = 'PM'

            op_str = '_' + op.upper() if op else ''
            sm_field = self.overpass_templ.format(orbit=op_str)
            if sm_field not in ds.keys():
                raise NameError(
                    sm_field,
                    'Field does not exists. Try deactivating overpass option.')

            if op_str == '_AM':
                op_str = ''
            else:
                op_str = '_pm'
            for parameter in self.parameters:
                metadata = {}
                param = ds[sm_field][parameter+op_str]
                data = np.flipud(param[:]).flatten()

                if self.grid is not None:
                    data = data[self.grid.activegpis]
                # mask according to valid_min, valid_max and _FillValue
                try:
                    fill_value = param.attrs['_FillValue']
                    valid_min = param.attrs['valid_min']
                    valid_max = param.attrs['valid_max']
                    data = np.where(
                        np.logical_or(data < valid_min, data > valid_max),
                        fill_value, data)
                except KeyError:
                    pass

                # fill metadata dictionary with metadata from image
                for key in param.attrs:
                    metadata[key] = param.attrs[key]

                ret_param_name = parameter

                if self.var_overpass_str:
                    if op is None:
                        warnings.warn(
                            'Renaming variable only possible if overpass in '
                            'given.'
                            ' Use names as in file.')
                        ret_param_name = parameter
                    elif not parameter.endswith(f'_{op.lower()}'):
                        ret_param_name = parameter + f'_{op.lower()}'

                return_data[ret_param_name] = data
                return_meta[ret_param_name] = metadata

        else:
            overpass_str = '_' + overpass.upper() if overpass else ''
            sm_field = self.overpass_templ.format(orbit=overpass_str)

            if sm_field not in ds.keys():
                raise NameError(
                    sm_field,
                    'Field does not exists. Try deactivating overpass option.')

            if overpass:
                overpass_str = '_pm' if overpass == 'PM' else ''
            else:
                overpass_str = ''

            for parameter in self.parameters:
                metadata = {}
                param = ds[sm_field][parameter + overpass_str]
                data = np.flipud(param[:]).flatten()

                if self.grid is not None:
                    data = data[self.grid.activegpis]
                # mask according to valid_min, valid_max and _FillValue
                try:
                    fill_value = param.attrs['_FillValue']
                    valid_min = param.attrs['valid_min']
                    valid_max = param.attrs['valid_max']
                    data = np.where(
                        np.logical_or(data < valid_min, data > valid_max),
                        fill_value, data)
                except KeyError:
                    pass

                # fill metadata dictionary with metadata from image
                for key in param.attrs:
                    metadata[key] = param.attrs[key]

                ret_param_name = parameter

                if self.var_overpass_str:
                    if overpass is None:
                        warnings.warn(
                            'Renaming variable only possible if overpass in '
                            'given.'
                            ' Use names as in file.')
                        ret_param_name = parameter
                    elif not parameter.endswith(f'_{overpass.lower()}'):
                        if parameter == 'tb_time_seconds':
                            # Keep tb_time_seconds unmodified
                            ret_param_name = parameter
                        else:
                            # Append overpass or maintain current logic for other parameters
                            ret_param_name = parameter + f'_{overpass.lower()}'
                        # ret_param_name = parameter + f'_{overpass.lower()}'

                return_data[ret_param_name] = data
                return_meta[ret_param_name] = metadata

        if overpass == 'BOTH':
            if counter > 0:
                overpass_change('overpass_state_AM')
                increment_counter('counter')
            else:
                increment_counter('counter')
            keys_pm = [element + '_pm' if isinstance(element, str) else element
                       for element in self.parameters]
            keys_am = [element + '_am' if isinstance(element, str) else element
                       for element in self.parameters]


            if op == 'AM':

                return_data_am = {k: return_data[k] for k in keys_am}
                return_data_am = {self.parameters[i]: value for i, (key, value)
                                  in enumerate(return_data_am.items())}
                return_meta_am = {k: return_meta[k] for k in keys_am}
                return_meta = {self.parameters[i]: value for i, (key, value) in
                               enumerate(return_meta_am.items())}
                df_returndata = pd.DataFrame.from_dict(return_data_am)
                df_returndata['Overpass'] = 1
            elif op == 'PM':
                return_data_pm = {k: return_data[k] for k in keys_pm}
                return_data_pm = {self.parameters[i]: value for i, (key, value)
                                  in enumerate(return_data_pm.items())}
                return_meta_pm = {k: return_meta[k] for k in keys_pm}
                return_meta = {self.parameters[i]: value for i, (key, value) in
                               enumerate(return_meta_pm.items())}
                df_returndata = pd.DataFrame.from_dict(return_data_pm)
                df_returndata['Overpass'] = 2

            return_data = {col: df_returndata[col].to_numpy() for col in
                           df_returndata.columns}
            return_meta['Overpass'] = {'_FillValue': -9999, 'valid_min': 1,
                                       'valid_max': 2}
        else:

            if overpass == 'AM':
                if self.var_overpass_str:
                    return_data = return_data

                else:
                    pass
            elif overpass == 'PM':
                if self.var_overpass_str:


                    return_data = return_data

                else:
                    pass


        if self.flatten:
            return Image(self.grid.activearrlon, self.grid.activearrlat,
                         return_data, return_meta, timestamp,
                         timekey=self.time_key)
        else:

            if len(self.grid.subset_shape) != 2:
                raise ValueError(
                    "Grid is 1-dimensional, to read a 2d image,"
                    " a 2d grid - e.g. from bbox of the global grid -"
                    "is required.")

            if (np.prod(self.grid.subset_shape) != len(
                    self.grid.activearrlon)) or \
                    (np.prod(self.grid.subset_shape) != len(
                        self.grid.activearrlat)):
                raise ValueError(
                    f"The grid shape {self.grid.subset_shape} "
                    f"does not match with the shape of the loaded "
                    f"data. If you have passed a subgrid with gaps"
                    f" (e.g. landpoints only) you have to set"
                    f" `flatten=True`")

            lons = np.flipud(
                self.grid.activearrlon.reshape(self.grid.subset_shape))
            lats = np.flipud(
                self.grid.activearrlat.reshape(self.grid.subset_shape))
            data = {
                param: np.flipud(data.reshape(self.grid.subset_shape))
                for param, data in return_data.items()
            }

            return Image(lons, lats, data, return_meta, timestamp,
                         timekey=self.time_key)

    def write(self, data):
        raise NotImplementedError()

    def flush(self):
        pass

    def close(self):
        pass


class SPL3SMP_Ds(MultiTemporalImageBase):
    """
    Class for reading a collection of SMAP Level 3 Passive Soil Moisture
    images.

    Parameters
    ----------
    data_path: str
        root path of the SMAP data files
    parameter : str or list, optional (default: 'soil_moisture')
        one or list of parameters found at
        http://nsidc.org/data/smap_io/spl3smp/data-fields
        Default : 'soil_moisture'
    overpass : str, optional (default: 'AM')
        Select 'AM' for the descending overpass or 'PM' for the ascending one.
        Dataset version must support multiple overpasses.
    var_overpass_str : bool, optional (default: True)
        Append overpass indicator to the loaded variables. E.g. Soil Moisture
        will be called soil_moisture_pm and soil_moisture_am, and soil_moisture
        in all cases if this is set to False.
    subpath_templ : list, optional (default: ('%Y.%m.%d',))
        If the data is store in subpaths based on the date of the dataset
        then this list
        can be used to specify the paths. Every list element specifies one
        path level.
    crid : int, optional (default: None)
        Only read files with this specific Composite Release ID.
        See also https://nsidc.org/data/smap/data_versions#CRID
    grid: pygeogrids.CellGrid, optional (default: None)
        A (sub)grid of points to read. e.g. to read data for land points only
        for a specific bounding box. Must be a subgrid of an EASE25 Grid.
        If None is passed, all point are read.
    flatten: bool, optional (default: False)
        If true the read data will be returned as 1D arrays.
    """

    def __init__(self,
                 data_path,
                 subpath_templ=('%Y.%m.%d',),
                 crid=None,
                 parameter='soil_moisture',
                 overpass='AM',
                 time_key='tb_time_seconds',
                 var_overpass_str=True,
                 grid=None,
                 flatten=False,):

        if crid is None:
            filename_templ = f"SMAP_L3_SM_P_{'{datetime}'}_*.h5"
        else:
            filename_templ = f"SMAP_L3_SM_P_{'{datetime}'}_R{crid}*.h5"

        ioclass_kws = {
            'parameter': parameter,
            'overpass': overpass,
            'var_overpass_str': var_overpass_str,
            'grid': grid,
            'flatten': flatten,
            'time_key': time_key
        }

        super().__init__(
            data_path,
            SPL3SMP_Img,
            fname_templ=filename_templ,
            datetime_format="%Y%m%d",
            subpath_templ=subpath_templ,
            exact_templ=False,
            ioclass_kws=ioclass_kws)
        self.overpass = overpass

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
        if self.overpass == 'BOTH':
            timestamps = [item for item in timestamps for _ in range(2)]
        else:
            pass
        return timestamps

    def _build_filename(self, timestamp, custom_templ=None,
                        str_param=None):
        """
        SMAP files can be ambiguous. Multiple (reprocessed) versions
        of an image can be present. In this case we sort the files
        and use the last one ovailable.
        -- Override base function.
        This function uses _search_files to find the correct
        filename and checks if the search was unambiguous

        Parameters
        ----------
        timestamp: datetime
            datetime for given filename
        custom_tmpl : string, optional
            If given the fname_templ is not used but the custom_templ. This
            is convenient for some datasets where not all file names follow
            the same convention and where the read_image function can choose
            between templates based on some condition.
        str_param : dict, optional
            If given then this dict will be applied to the fname_templ using
            the fname_templ.format(**str_param) notation before the resulting
            string is put into datetime.strftime.

            example from python documentation
            >>> coord = {'latitude': '37.24N', 'longitude': '-115.81W'}
            >>> 'Coordinates: {latitude}, {longitude}'.format(**coord)
            'Coordinates: 37.24N, -115.81W'
        """
        filename = self._search_files(timestamp, custom_templ=custom_templ,
                                      str_param=str_param)
        if len(filename) == 0:
            raise IOError("No file found for {:}".format(timestamp.ctime()))
        if len(filename) > 1:
            warnings.warn(
                f"File search is ambiguous for timestamp {timestamp}: "
                f"{filename}. "
                f"Sorting and using last file, with the higher CRID: "
                f"{sorted(filename)[-1]}"
            )
            filename = sorted(filename)
        # filenames = sorted(filename)

        return filename[-1]


class SMAPTs(GriddedNcOrthoMultiTs):

    def __init__(self, ts_path, grid_path=None, **kwargs):
        """
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
                Specific variable names to read, if None are selected,
                all are read.
            offsets : dict, optional (default:None)
                Offsets (values) that are added to the parameters (keys)
            scale_factors : dict, optional (default:None)
                Offset (value) that the parameters (key) is multiplied with
            ioclass_kws: dict, (optional)
                Optional keyword arguments to pass to OrthoMultiTs class:
                ----------------------------------------------------------------
                    read_bulk : boolean, optional (default:False)
                        if set to True the data of all locations is read
                        into memory,
                        and subsequent calls to read_ts read from the cache and
                        not from disk this makes reading complete files faster
                    read_dates : boolean, optional (default:False)
                        if false dates will not be read automatically but
                        only on
                        specific request useable for bulk reading because
                        currently
                        the netCDF num2date routine is very slow for big
                        datasets.
        """

        if grid_path is None:
            grid_path = os.path.join(ts_path, "grid.nc")

        grid = ncdf.load_grid(grid_path)
        super(SMAPTs, self).__init__(ts_path, grid, **kwargs)


class SMAPL3_V9Reader(GriddedNcIndexedRaggedTs):
    """
        Class for reading SMAP Level 3 version 9 time series data. Provides
        methods to
        load and filter soil moisture datasets for further processing. This
        class is
        compatible with NetCDF files and supports indexed ragged time-series
        formats.

        Parameters
        ----------
        ts_path : str
            Directory where the netcdf time series files are stored
    """

    def __init__(self, *args, **kwargs):
        if os.path.exists(os.path.join(args[0], "grid.nc")):
            grid = load_grid(os.path.join(args[0], "grid.nc"))
        else:
            grid = None
        kwargs['grid'] = grid
        super().__init__(*args, **kwargs)

    def read(self, *args, **kwargs) -> pd.DataFrame:
        ts = super().read(*args, **kwargs)
        if (ts is not None) and not ts.empty:
            ts = ts[ts.index.notnull()]
            for col in ['soil_moisture_error', "retrieval_qual_flag",
                        "freeze_thaw_fraction", "surface_flag",
                        "surface_temperature", "vegetation_opacity",
                        "vegetation_water_content", "landcover_class",
                        'static_water_body_fraction']:
                if col in ts.columns:
                    ts[col] = ts[col].fillna(0)
            if 'soil_moisture' in ts.columns:
                ts = ts.dropna(subset='soil_moisture')
                ts = ts.sort_index()
        assert ts is not None, "No data read"
        return ts


class ReaderWithExtension_SMAP():
    """
        Concatenate 2 time series upon reading
        """

    def __init__(self, cls, path, path_ext, *args, **kwargs):
        """
        Parameters
        ----------
        cls: Callable
            Reader class to wrap
        path: str
            Path to the main time series (not the extension dataset)
        path_ext: str
            Extension time series path
        args, kwargs:
            Additional arguments to set up the readers
        """
        self.base_reader = cls(path, *args, **kwargs)
        try:
            self.ext_reader = cls(path_ext, *args, **kwargs)
        except FileNotFoundError:
            logging.error(f"No extension dataset found in path {path_ext}")
            self.ext_reader = None

    @property
    def grid(self):
        return self.base_reader.grid

    def read(self, *args, **kwargs) -> pd.DataFrame:
        """
        Read time series at location for both the base dataset and the
        extension. If extension is read, concatenate both in time.
        """
        try:
            if self.ext_reader is not None:
                ts = self.ext_reader.read(*args, **kwargs)
            else:
                ts = self.base_reader.read(*args, **kwargs)
        except Exception as e:
            logging.error(f"Extension reading failed for {args} {kwargs} with"
                          f"error: {e}")

        return ts




def organize_smap_files(root_dir, start_date=None, end_date=None, file_pattern=None):
    """
    Scans all subdirectories under `root_dir` for files matching:
        SMAP_L3_SM_P_YYYYMMDD_R#####_###.h5
    Creates a 'temp' folder in `root_dir` containing subfolders named by date (YYYY.MM.DD),
    and copies each file into its respective date folder.
    Also copies 'grid.nc' from the root directory into 'temp'.

    Optional:
        start_date (str): Include files on or after this date, format 'YYYY-MM-DD'.
        end_date (str): Include files on or before this date, format 'YYYY-MM-DD'.

    Example:
        organize_smap_files("/path/to/data", start_date="2025-01-01", end_date="2025-12-31")
        SMAP_L3_SM_P_20251018_R19240_002.h5 → root_dir/temp/2025.10.18/
        grid.nc → root_dir/temp/grid.nc
    """
    # Create 'temp' directory in root
    temp_dir = os.path.join(root_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Regex for filenames like SMAP_L3_SM_P_20251018_R19240_002.h5
    if file_pattern is None:
        smap_pattern = re.compile(r"^SMAP_L3_SM_P_(\d{8})_R\d{5}_\d{3}\.h5$")
    else:
        smap_pattern = re.compile(file_pattern)

    # Convert start and end dates to datetime objects (if provided)
    def parse_date(date_str):
        return datetime.strptime(date_str, "%Y-%m-%d")
    if type(start_date) == str:
        start_dt = parse_date(start_date) if start_date else None
        end_dt = parse_date(end_date) if end_date else None
    else:
        start_dt = start_date
        end_dt = end_date

    copied_files = 0

    # Walk through all subdirectories
    for dirpath, _, filenames in os.walk(root_dir):
        # Skip the 'temp' directory to avoid recursive copying
        if dirpath.startswith(temp_dir):
            continue

        for filename in filenames:
            match = smap_pattern.match(filename)
            if match:
                date_str = match.group(1)  # 'YYYYMMDD'
                file_date = datetime.strptime(date_str, "%Y%m%d")

                # Apply inclusive date range filtering
                if start_dt and file_date < start_dt:
                    continue
                if end_dt and file_date > end_dt:
                    continue

                # Create destination folder by date
                folder_name = f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:8]}"
                target_folder = os.path.join(temp_dir, folder_name)
                os.makedirs(target_folder, exist_ok=True)

                source_file = os.path.join(dirpath, filename)
                dest_file = os.path.join(target_folder, filename)

                shutil.copy2(source_file, dest_file)  # copy file with metadata
                copied_files += 1
                print(f"Copied: {filename} → {target_folder}")

    # Copy grid.nc if it exists in root_dir
    grid_path = os.path.join(root_dir, "grid.nc")
    if os.path.isfile(grid_path):
        shutil.copy2(grid_path, os.path.join(temp_dir, "grid.nc"))
        print(f"\nCopied: grid.nc → {temp_dir}")
    else:
        print("\n⚠️ grid.nc not found in the root directory.")

    if copied_files == 0:
        print("\n⚠️ No SMAP files matched the given date range.")
    else:
        print(f"\n✅ {copied_files} SMAP files organized in: {temp_dir}")







def get_max_time_from_netcdfs(folder_path: str, time_var: str = "time") -> float:
    """
    Find the overall maximum valid value for the 'time' variable across
    all NetCDF files in a folder.

    Parameters
    ----------
    folder_path : str
        Path to the folder containing NetCDF files.
    time_var : str, optional
        Name of the time variable to extract (default is 'time').

    Returns
    -------
    float
        The maximum valid (non-NaN, finite) value of the time variable
        across all files. Returns None if no valid time values are found.
    """
    max_time = None

    # Collect all NetCDF files in the directory
    nc_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.endswith((".nc", ".nc4", ".cdf"))
    ]

    if not nc_files:
        print("No NetCDF files found in the given folder.")
        return None

    for f in nc_files:
        try:
            with xr.open_dataset(f) as ds:
                print(f"Reading {f}...")
                if time_var not in ds:
                    continue

                # Extract the time variable and convert to a NumPy array
                time_values = ds[time_var].values

                # Mask invalid or non-finite entries
                time_values = np.asarray(time_values)
                time_values = time_values[np.isfinite(time_values)]

                if time_values.size > 0:
                    file_max = np.max(time_values)
                    if max_time is None or file_max > max_time:
                        max_time = file_max
        except Exception as e:
            print(f"Warning: Could not read {f} ({e})")

    return max_time

def get_min_time_from_netcdfs(folder_path: str, time_var: str = "time") -> float:
    """
    Find the overall maximum valid value for the 'time' variable across
    all NetCDF files in a folder.

    Parameters
    ----------
    folder_path : str
        Path to the folder containing NetCDF files.
    time_var : str, optional
        Name of the time variable to extract (default is 'time').

    Returns
    -------
    float
        The maximum valid (non-NaN, finite) value of the time variable
        across all files. Returns None if no valid time values are found.
    """
    min_time = None

    # Collect all NetCDF files in the directory
    nc_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.endswith((".nc", ".nc4", ".cdf"))
    ]

    if not nc_files:
        print("No NetCDF files found in the given folder.")
        return None

    for f in nc_files:
        try:
            with xr.open_dataset(f) as ds:
                print(f"Reading {f}...")
                if time_var not in ds:
                    continue

                # Extract the time variable and convert to a NumPy array
                time_values = ds[time_var].values

                # Mask invalid or non-finite entries
                time_values = np.asarray(time_values)
                time_values = time_values[np.isfinite(time_values)]

                if time_values.size > 0:
                    file_min = np.min(time_values)
                    if min_time is None or file_min > max_time:
                        max_time = file_min
        except Exception as e:
            print(f"Warning: Could not read {f} ({e})")

    return min_time



def merge_smap_folders(folder1, folder2, output_folder, time_key="time"):
    """
    Merge SMAP L3 NetCDF files from two folders by matching filenames.
    Assumes all files with the same name have identical locations/coordinates,
    and only the time dimension differs.

    After successfully merging, deletes the original two files.

    Parameters:
        folder1 (str): Path to the first folder of NetCDF files.
        folder2 (str): Path to the second folder of NetCDF files.
        output_folder (str): Path to save merged NetCDF files.
        time_key (str): Name of the time dimension (default: "time").
    """
    os.makedirs(output_folder, exist_ok=True)
    print(f"Output folder: {output_folder}")

    # List files in both folders
    files1 = {f for f in os.listdir(folder1) if f.endswith(".nc")}
    files2 = {f for f in os.listdir(folder2) if f.endswith(".nc")}

    # Find matching files
    common_files = files1 & files2
    if not common_files:
        print("No matching files found in the two folders.")
        return

    for fname in sorted(common_files):
        path1 = os.path.join(folder1, fname)
        path2 = os.path.join(folder2, fname)
        output_path = os.path.join(output_folder, fname)

        print(f"Merging: {fname}")
        try:
            # Open and merge along time
            ds1 = xr.open_dataset(path1)
            ds2 = xr.open_dataset(path2)
            merged = xr.concat([ds1, ds2], dim=time_key)

            # Save merged file
            merged.to_netcdf(output_path)
            print(f"✅ Merged file saved: {output_path}")

            # Close datasets before deleting
            ds1.close()
            ds2.close()
            merged.close()

            # Delete original files
            os.remove(path1)
            os.remove(path2)
            print(f"🗑️ Deleted original files:\n - {path1}\n - {path2}")

        except Exception as e:
            print(f"❌ Failed to merge {fname}: {e}")




