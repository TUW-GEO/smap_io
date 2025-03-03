from repurpose.process import parallel_process, idx_chunks
import pynetcf.time_series as nc
from pygeogrids.grids import CellGrid
import repurpose.resample as resamp
import numpy as np
import os
import time
from datetime import datetime
import logging
import pygeogrids.netcdf as grid2nc
import pandas as pd
from pygeobase.object_base import Image
import warnings

class Img2TsError(Exception):
    pass

def is_subset_grid(grid, other, compare_index=False, compare_cell=False):
    """
    Check if all the locations from other grid are also included
    in grid, i.e. other grid is a subset of grid.
    - Check if distance between (common) GPIs is 0

    Parameters
    ----------
    grid: CellGrid
        Main grid
    other: CellGrid
        Potential subset grid
    compare_index: bool, optional (default: False)
        If GPIs have the same coordinates, verify that the index is the same.
    compare_cell: bool, optional (default: True)
        Both input grids must be CellGrids.
        Also the cell numbers assigned to the same locations must be equal.

    Returns
    -------
    subset: bool
        True if subset or equal else False
    """
    gpis, dist = grid.find_nearest_gpi(other.activearrlon, other.activearrlat)

    if not np.all(dist == 0):
        return False

    if compare_index or compare_cell:
        grid = grid.subgrid_from_gpis(gpis)  # continue with common gpis
        if compare_index:
            if not np.array_equal(grid.activegpis, other.activegpis):
                return False
        if compare_cell:
            if (not isinstance(grid, CellGrid)) or \
               (not isinstance(other, CellGrid)):
                raise IOError("Both grids must be of of type `CellGrid`")
            if not np.array_equal(grid.activearrcell, other.activearrcell):
                return False

    return True


class Img2Ts:
    """
    class that uses the read_img iterator of the input_data dataset
    to read all images between startdate and enddate and saves them
    in netCDF time series files with the cell structure of the outputgrid.

    Currently, 2 time series formats are implemented:
      - The `OrthoMultiTs` format will we used when the same time stamp
        applies to all data points in a loaded image.
      - `IndexedRaggedTs` format will be used when time stamps vary between
        locations in a netcdf image file.
    The `_read_image` function will decide whether the orthogonal format is
    used or not.
    """

    def __init__(self,
                 input_dataset, outputpath, startdate, enddate,
                 input_kwargs=None, input_grid=None, target_grid=None,
                 imgbuffer=100, variable_rename=None, unlim_chunksize=100,
                 cellsize_lat=None, cellsize_lon=None,
                 r_methods='nn', r_weightf=None, r_min_n=1, r_radius=18000,
                 r_neigh=8, r_fill_values=None, filename_templ='%04d.nc',
                 gridname='grid.nc', global_attr=None, ts_attributes=None,
                 ts_dtypes=None, time_units="days since 1858-11-17 00:00:00",
                 zlib=True, n_proc=1, ignore_errors=False, backend='threading', exclude_missing_time_stamps = True, overpass='AM', elements_per_folders=None):
        """
        Parameters
        ----------
        input_dataset : DatasetImgBase like class instance
            must implement a ``read(date, **input_kwargs)`` iterator that returns a
            `pygeobase.object_base.Image` object that contains the data loaded
            from the netcdf file.
        outputpath : str
            path where to save the time series to
        startdate : datetime.datetime or str
            date from which the time series should start. Of course images
            have to be available from this date onwards.
        enddate : datetime.datetime or str
            date when the time series should end. Images should be available
            up until this date
        input_kwargs : dict, optional (default: None)
            keyword arguments which should be passed to the method
            ``read(date, **input_kwargs)`` to read the image data in addition
            to the time stamp.
        input_grid : CellGrid, optional (default: None)
            Ghe grid on which input data is stored.
            If not given then the grid of the input dataset will be used
            (`input_dataset.grid`)
            If the input dataset has no grid object then resampling to the
            target_grid is performed.
        target_grid : CellGrid, optional
            the grid on which the time series will be stored.
            If not given then the grid of the input dataset will be used
        imgbuffer : int, optional
            number of days worth of images that should be read into memory before
            a time series is written. This parameter should be chosen so that
            the memory of your machine is utilized. It depends on the daily data
            volume of the input dataset. If -1 is passed, all available
            data will be loaded at once (no buffer).
        variable_rename : dict, optional
            if the variables should have other names than the names that are
            returned as keys in the dict by the daily_images iterator. A dictionary
            can be provided that changes these names for the time series.
        unlim_chunksize : int, optional
            netCDF chunksize for unlimited variables.
        cellsize_lat : float, optional (default: None)
            if outgrid or input_data.grid are not cell grids then the cellsize
            in latitude direction must be specified here. Consider e.g. 5 deg
            cells as shown here for a grid with the origin in the bottom left corner:
            https://gldas.readthedocs.io/en/latest/_images/5x5_cell_partitioning.png
        cellsize_lon : float, optional (default: None)
            if outgrid or input_data.grid are not cell grids then the cellsize
            in longitude direction must be specified here. Consider e.g. 5 deg
            cells as shown here for a grid with the origin in the bottom left corner:
            https://gldas.readthedocs.io/en/latest/_images/5x5_cell_partitioning.png
        r_methods : string or dict, optional
            resample methods to use if resampling is necessary, either 'nn' for
            nearest neighbour or 'custom' for custom weight function.
            Can also be a dictionary in which the method is specified for each
            variable
        r_weightf : function or dict, optional
            if r_methods is custom this function will be used to calculate the
            weights depending on distance. This can also be a dict with a separate
            weight function for each variable.
        r_min_n : int, optional
            Minimum number of neighbours on the target_grid that are required for
            a point to be resampled.
        r_radius : float, optional
            resample radius in which neighbours should be searched given in meters
        r_neigh : int, optional
            maximum number of neighbours found inside r_radius to use during
            resampling. If more are found the r_neigh closest neighbours will be
            used.
        r_fill_values : number or dict, optional
            if given the resampled output array will be filled with this value if
            no valid resampled value could be computed, if not a masked array will
            be returned can also be a dict with a fill value for each variable
        filename_templ : string, optional
            filename template must be a string with a string formatter for the
            cell number.
            e.g. '%04d.nc' will translate to the filename '0001.nc' for cell
            number 1.
        gridname : string, optional
            filename of the grid which will be saved as netCDF
        global_attr : dict, optional
            global attributes for each file
        ts_attributes : dict, optional
            dictionary of attributes that should be set for the netCDF time series.
            Can be either a dictionary of attributes that will be set for all
            variables in input_data or a dictionary of dictionaries.
            In the second case the first dictionary has to have a key for each
            variable returned by input_data and the second level dictionary will be
            the dictionary of attributes for this time series.
        ts_dtype : numpy.dtype or dict of numpy.dtypes
            data type to use for the time series, if it is a dict then a key must
            exist for each variable returned by input_data.
            Default : None, no change from input data
        time_units : string, optional
            units the time axis is given in.
            Default: "days since  1858-11-17 00:00:00" which is modified julian
            date for regular images this can be set freely since the conversion
            is done automatically, for images with irregular timestamp this will
            be ignored for now
        zlib: boolean, optional (default: True)
            if True the saved netCDF files will be compressed
            Default: True
        n_proc: int, optional (default: 1)
            Number of parallel processes. Multiprocessing is only used when
            `n_proc` > 1. Applies to data reading and writing. Should be chosen
            according to the file connection. A slow connection might be overloaded
            by too many processes trying to read data (e.g. network).
            If unsure, better leave this at 1.
        ignore_errors: bool, optional (default: False)
            Instead of raising an exception, log errors and continue the
            process. E.g. to skip individual corrupt files.
        backend: str, optional (default: 'threading')
            Which backend joblib should use. Default is 'threading',
            other options are 'multiprocessing' and 'loky'
        """

        self.backend = backend
        self.imgin = input_dataset
        self.zlib = zlib
        self.exclude_missing_time_stamps = exclude_missing_time_stamps
        self.overpass = overpass

        if (input_grid is None) and hasattr(self.imgin, 'grid'):
            input_grid = self.imgin.grid

        self.input_grid = input_grid
        self.target_grid = target_grid

        if self.target_grid is None:
            self.target_grid = self.input_grid

        if self.input_grid is None and self.target_grid is None:
            raise ValueError("Either the input dataset has to have a grid, "
                             "`input_grid` has to be specified or "
                             "`target_grid` has to be set")

        self.input_kwargs = input_kwargs or dict()

        # Chunk the target grid according to the chosen cell size
        if not hasattr(self.target_grid, 'activearrcell'):
            if (cellsize_lat is None) or (cellsize_lon is None):
                raise ValueError(
                    "Target grid is not a CellGrid. `cellsize_lat` and "
                    "`cellsize_lon` must be specified")
            self.target_grid = self.target_grid.to_cell_grid(
                cellsize_lat=cellsize_lat, cellsize_lon=cellsize_lon)
        else:
            if cellsize_lat is not None or cellsize_lon is not None:
                warnings.warn("A cell size was specified, but the input grid "
                              "is already a CellGrid. Your settings will be"
                              "ignored!")

        if self.input_grid is None:
            self.resample = True
        elif (hasattr(self.input_grid, 'activearrcell') and
              hasattr(self.target_grid, 'activearrcell') and
              (self.input_grid == self.target_grid)):
            self.resample = False
        elif is_subset_grid(self.input_grid, self.target_grid, compare_index=True):
            # even if grids are the same, but GPI order is different, resample
            self.resample = False
        else:
            self.resample = True

        startdate = pd.to_datetime(startdate).to_pydatetime()
        enddate = pd.to_datetime(enddate).to_pydatetime()

        self.currentdate = startdate
        self.startdate = startdate
        self.enddate = enddate
        self.imgbuffer = imgbuffer
        self.outputpath = outputpath
        self.variable_rename = variable_rename
        self.unlim_chunksize = unlim_chunksize
        self.gridname = gridname
        self.elements_per_folders = elements_per_folders
        self.r_methods = r_methods
        self.r_weightf = r_weightf
        self.r_min_n = r_min_n
        self.r_radius = r_radius
        self.r_neigh = r_neigh
        self.r_fill_values = r_fill_values

        self.filename_templ = filename_templ
        self.global_attr = global_attr
        self.ts_attributes = ts_attributes
        self.ts_dtypes = ts_dtypes
        self.time_units = time_units

        self.ignore_errors = ignore_errors

        # if each image has only one timestamp then we are handling
        # time series of type Orthogonal multidimensional array representation
        # according to the CF conventions.
        # The following are detected from data and set during reading
        self.orthogonal = None  # to be set when reading data
        self.timekey = None  # to be set when reading data

        self.n_proc = n_proc

        self.log_filename = \
            f"img2ts_{datetime.now().strftime('%Y%m%d%H%M')}.log"


    def _read_image(self, date, input_grid, target_grid):
        """
        Function to parallelize reading image data from dataset.
        Do not modify any class attributes here!

        Parameters
        ----------
        date: datetime.datetime
            Time stamp of the image to read. This is used by the image stack
            reader to extract a data array.
        input_grid: CellGrid
            Grid containing the points that image stack reader loads.
        target_grid: CellGrid
            To perform spatial resampling, a target grid is needed. If None is
            given or the target grid is the same as the input grid, then no
            spatial resampling is performed.

        Returns
        -------
        image: Image
            Image data read from input data set (might be spatially resampled)
        orthogonal: bool
            Whether the image fits the orthogonal time series format or not.
        """
        logger = logging.getLogger('img2ts')

        # optional on-the-fly spatial resampling
        resample_kwargs = {
            'methods': self.r_methods,
            'weight_funcs': self.r_weightf,
            'min_neighbours': self.r_min_n,
            'search_rad': self.r_radius,
            'neighbours': self.r_neigh,
            'fill_values': self.r_fill_values,
        }

        logger.info(f"Read image at: {str(date)}")

        try:
            image = self.imgin.read(date, **self.input_kwargs)

            # if input grid is not set, use grid from image
            # this makes sense if data/image is on a swath orbit grid
            # and changing from image to image
            if input_grid is None:
                input_grid = image.grid
        except IOError as e:
            msg = "I/O error({0}): {1}".format(e.errno,
                                               e.strerror)
            logger.info(msg)
            image = None

        if image is None:
            logger.info(f"Could not read image at date {date}.")
            return None

        if self.resample:
            logger.info("Grids don't match. Spatial resampling is performed.")
            # resample with subset selection (NN)
            if target_grid is None:
                raise Img2TsError("Target grid is required for spatial "
                                  "resampling.")
            else:
                data = resamp.resample_to_grid(
                    image.data, image.lon, image.lat,
                    target_grid.activearrlon,
                    target_grid.activearrlat,
                    **resample_kwargs)

                # new image instance with resampled data
                metadata = image.metadata
                metadata["resampling_date"] = f"{datetime.now()}"

                image = Image(target_grid.activearrlon,
                              target_grid.activearrlat,
                              data=data,
                              metadata=metadata,
                              timestamp=image.timestamp,
                              timekey=image.timekey,
                              )
        elif len(target_grid.activegpis) != len(input_grid.activegpis):
            logger.info("Grids have different size, sub-setting is performed.")
            # grid is the same but subset is loaded
            metadata = image.metadata
            metadata["subsetting_date"] = f"{datetime.now()}"

            idx = np.where(np.isin(input_grid.activegpis, target_grid.activegpis))
            image = Image(target_grid.activearrlon,
                          target_grid.activearrlat,
                          data={k: v[idx] for k, v in image.data.items()},
                          metadata=metadata,
                          timestamp=image.timestamp,
                          timekey=image.timekey,
                          )
        else:
            # no sub-setting or resampling required, take the image data as is
            pass

        orthogonal = self.orthogonal

        if image.timekey is not None:
            # if time_arr is not None means that each observation of the
            # image has its own observation time
            # this means that the resulting time series is not
            # regularly spaced in time
            if orthogonal is None:
                logger.info("Setting mode to NON-ORTHOGONAL image format")
                orthogonal = False
            else:
                if orthogonal:
                    raise Img2TsError(
                        "Images can not switch between a fixed image "
                        "timestamp and individual timestamps for each "
                        "observation")
        else:
            if orthogonal is None:
                logger.info("Use ORTHOGONAL image format")
                orthogonal = True
            else:
                if not orthogonal:
                    raise Img2TsError(
                        "Images can not switch between a fixed image "
                        "timestamp and individual timestamps for each "
                        "observation")

        return image, orthogonal

    def _write_orthogonal(self,
                          cell: int,
                          cell_gpis: np.ndarray,
                          cell_lons: np.ndarray,
                          cell_lats: np.ndarray,
                          timestamps: np.ndarray,
                          **celldata):
        """
        Write time series in OrthoMultiTs format.

        Parameters
        ----------
        cell: int
            Cell number of the data to write
        cell_gpis: np.ndarray
            GPIs of data to write. Must match with celldata / lons / lats
        cell_lons: np.ndarray
            Lons of data to write. Must match with celldata / gpis / lats
        cell_lats: np.ndarray
            Lats of data to write. Must match with celldata / gpis / lons
        timestamps: np.ndarray
            Array of datetime objects with same size as second dimension of
            data arrays.
        **celldata:
            Data variable names as keys and 2D numpy.arrays as values
        """
        logger = logging.getLogger('img2ts')  # can be used to write to file

        logger.info(f"Appending orthogonal time series chunk for cell {cell}")

        while True:
            try:
                with nc.OrthoMultiTs(
                        os.path.join(self.outputpath,
                                     self.filename_templ % cell),
                        n_loc=cell_gpis.size, mode='a',
                        zlib=self.zlib,
                        unlim_chunksize=self.unlim_chunksize,
                        time_units=self.time_units) as dataout:

                    # add global attributes to file
                    if self.global_attr is not None:
                        for attr in self.global_attr:
                            dataout.add_global_attr(
                                attr, self.global_attr[attr])

                    dataout.add_global_attr('timeSeries_format',
                                            dataout.__class__.__name__)

                    dataout.add_global_attr(
                        'geospatial_lat_min', np.min(cell_lats))
                    dataout.add_global_attr(
                        'geospatial_lat_max', np.max(cell_lats))
                    dataout.add_global_attr(
                        'geospatial_lon_min', np.min(cell_lons))
                    dataout.add_global_attr(
                        'geospatial_lon_max', np.max(cell_lons))

                    dataout.write_all(cell_gpis, celldata, timestamps,
                                      lons=cell_lons, lats=cell_lats,
                                      attributes=self.ts_attributes)
                    break
            except OSError:  # file probably used by some other process
                logging.error(f"Could not write to file for cell {cell}. "
                              f"Wait a bit and try again...")
                time.sleep(3)


    def _write_non_orthogonal(self,
                              cell: int,
                              cell_gpis: np.ndarray,
                              cell_lons: np.ndarray,
                              cell_lats: np.ndarray,
                              **celldata):
        """
        Write time series data for cell to IndexedRagged format.

        Parameters
        ----------
        cell: int
            Cell number
        cell_gpis: np.ndarray
            GPIs of data to write. Must match with celldata / lons / lats
        cell_lons: np.ndarray
            Lons of data to write. Must match with celldata / gpis / lats
        cell_lats: np.ndarray
            Lats of data to write. Must match with celldata / gpis / lons
        celldata: dict[str, np.ndarray]
            Time series data for this cell.
            Arrays must be sorted by the GPI in the cell (asc.)
            arrays have the following shape [dates, ...]
        """
        logger = logging.getLogger('img2ts')  # can be used to write to file

        fname = os.path.join(self.outputpath, self.filename_templ % cell)

        n_gpis, n_t = celldata[self.timekey].shape
        gpis = np.repeat(cell_gpis, n_t)
        lons = np.repeat(cell_lons, n_t)
        lats = np.repeat(cell_lats, n_t)

        gpi_time = celldata.pop(self.timekey).flatten()

        # remove measurements that were filled with the fill value
        # during resampling
        # doing this on the basis of the time variable should
        # be enough since without time -> no valid
        # observations
        if self.resample:
            if self.r_fill_values is not None:
                if type(self.r_fill_values) == dict:
                    time_fill_value = self.r_fill_values[self.timekey]
                else:
                    time_fill_value = self.r_fill_values

                if isinstance(gpi_time, np.ma.masked_array):
                    valid_mask1 = np.invert(gpi_time.mask)
                else:
                    valid_mask1 = None

                if np.isnan(time_fill_value):
                    valid_mask = ~np.isnan(gpi_time)
                else:
                    valid_mask = gpi_time != time_fill_value

                if valid_mask1 is not None:
                    valid_mask = valid_mask & valid_mask1
            else:
                valid_mask = np.invert(gpi_time.mask)
        else:
            # drop data where time stamps are NaN
            valid_mask = np.isfinite(gpi_time)

        celldata = {k: v.flatten()[valid_mask].filled() for k, v in celldata.items()
                    if k != self.timekey}

        gpis, lons, lats = gpis[valid_mask], lons[valid_mask], lats[valid_mask]

        while True:
            try:
                with nc.IndexedRaggedTs(
                        fname,
                        n_loc=len(cell_gpis),  # no duplicates
                        mode='a',
                        zlib=self.zlib,
                        unlim_chunksize=self.unlim_chunksize,
                        time_units=self.time_units) as dataout:

                    # add global attributes to file
                    if self.global_attr is not None:
                        for attr in self.global_attr:
                            dataout.add_global_attr(
                                attr, self.global_attr[attr])

                    dataout.add_global_attr('timeSeries_format',
                                            dataout.__class__.__name__)

                    dataout.add_global_attr(
                        'geospatial_lat_min', np.min(cell_lats))
                    dataout.add_global_attr(
                        'geospatial_lat_max', np.max(cell_lats))
                    dataout.add_global_attr(
                        'geospatial_lon_min', np.min(cell_lons))
                    dataout.add_global_attr(
                        'geospatial_lon_max', np.max(cell_lons))

                    # var attr keys and celldata keys must match!
                    if self.timekey is not None and self.ts_attributes is not None:
                        if self.timekey in self.ts_attributes:
                            _ = self.ts_attributes.pop(self.timekey)

                    if self.exclude_missing_time_stamps:
                        time_id = np.where(gpi_time[valid_mask].filled() == -9999.)[0]
                        df_celldata = pd.DataFrame.from_dict(celldata)
                        df_celldata.drop(index=time_id, inplace=True)
                        gpis = np.delete(gpis, time_id)
                        lons = np.delete(lons, time_id)
                        lats = np.delete(lats, time_id)
                        time_array = np.delete(gpi_time[valid_mask].filled(), time_id)
                        celldata = {col: df_celldata[col].to_numpy() for col in df_celldata.columns}
                    else:
                        time_array = gpi_time[valid_mask].filled()





                    d = 1

                    # dataout.write(gpis, celldata, gpi_time[valid_mask].filled(),
                    #               lon=lons, lat=lats,
                    #               attributes=self.ts_attributes,
                    #               dates_direct=True)
                    dataout.write(gpis, celldata, time_array,
                                  lon=lons, lat=lats,
                                  attributes=self.ts_attributes,
                                  dates_direct=True)

                    logger.info(f"Non-Orthogonal time series chunk for cell {cell} "
                                f"written.")
                    break
            except OSError:  # file probably used by some other process
                logging.error(f"Could not write to file for cell {cell}. "
                              f"Wait a bit and try again...")
                time.sleep(3)


    def calc(self):
        """
        Iterate through all images of the image stack and extract temporal
        chunks. Transpose the data and append it to the output time series
        files.
        """
        # save grid information in file
        grid2nc.save_grid(
            os.path.join(self.outputpath, self.gridname), self.target_grid)

        for img_stack_dict, timestamps in self.img_bulk():
            # =================================================================
            logging.info(f"Finished reading bulk with {len(timestamps)} images")

            start_time = datetime.now()

            # temporally drop grids, due to issue when pickling them...
            target_grid = self.target_grid
            input_grid = self.input_grid
            self.target_grid = None
            self.input_grid = None

            _cells = target_grid.activearrcell

            # the goal is to select data by cell and sort by gpi
            cells_sorted = np.all(_cells[:-1] <= _cells[1:])

            if not cells_sorted:
                cells_order = np.argsort(_cells)
            else:
                cells_order = None

            keys = list(img_stack_dict.keys())
            for key in keys:
                #print(key)
                # rename variable in output dataset
                if self.variable_rename is None:
                    var_new_name = str(key)
                else:
                    var_new_name = self.variable_rename[key]

                # change dtypes of output time series
                if self.ts_dtypes is not None:
                    if type(self.ts_dtypes) == dict:
                        output_dtype = self.ts_dtypes[key]
                    else:
                        output_dtype = self.ts_dtypes
                    img_stack_dict[key] = img_stack_dict[key].astype(
                        output_dtype)

                if var_new_name != key:
                    img_stack_dict[var_new_name] = img_stack_dict[key]
                    del img_stack_dict[key]

                if cells_order is not None:
                    # Pass the data sorted by cell GPIs to store them
                    img_stack_dict[var_new_name] = \
                        img_stack_dict[var_new_name][:, cells_order]

            if cells_order is not None:
                # sort the grid so it matches the data!
                # the funny sorting allows to use np.split later
                _grid = CellGrid(lon=target_grid.activearrlon[cells_order],
                                 lat=target_grid.activearrlat[cells_order],
                                 gpis=target_grid.activegpis[cells_order],
                                 cells=target_grid.activearrcell[cells_order])
            else:
                _grid = target_grid

            ITER_KWARGS = {}
            # check if target_grid.activearrcell is sorted
            # if not sort it and the arrays accordingly
            values, indices, counts = np.unique(
                _grid.activearrcell, return_counts=True, return_index=True)

            ITER_KWARGS['cell'] = values
            for k, v in img_stack_dict.items():
                # split data by cell
                v = np.split(np.swapaxes(np.atleast_2d(v), 0, 1),
                             indices, axis=0)[1:]
                ITER_KWARGS[k] = v

            del img_stack_dict

            ITER_KWARGS['cell_gpis'] = np.split(_grid.activegpis, indices)[1:]
            ITER_KWARGS['cell_lons'] = np.split(_grid.activearrlon, indices)[1:]
            ITER_KWARGS['cell_lats'] = np.split(_grid.activearrlat, indices)[1:]

            STATIC_KWARGS = {}
            if self.orthogonal:
                STATIC_KWARGS['timestamps'] = timestamps
                FUNC = self._write_orthogonal
            else:
                # time information is contained in `celldata`
                FUNC = self._write_non_orthogonal

            if self.global_attr is None:
                self.global_attr = {}

            try:
                self.global_attr['time_coverage_end'] = str(timestamps[-1])
            except IndexError:  # this can be the case if a whole bulk is empty
                warnings.warn("Could not infer time coverage from files")
                self.global_attr['time_coverage_end'] = "unknown"

            parallel_process(
                FUNC=FUNC,
                ITER_KWARGS=ITER_KWARGS,
                STATIC_KWARGS=STATIC_KWARGS,
                log_path=os.path.join(self.outputpath, '000_log'),
                log_filename=self.log_filename,
                loglevel="WARNING",
                logger_name='img2ts',
                ignore_errors=self.ignore_errors,
                n_proc=self.n_proc,
                show_progress_bars=False,
                backend=self.backend,
            )

            self.target_grid = target_grid
            self.input_grid = input_grid

            del ITER_KWARGS, STATIC_KWARGS

            logger = logging.getLogger('img2ts')
            logger.info(f"Chunk processed in "
                        f"{datetime.now() - start_time} Seconds")

    # def create_multiple_copies_for_timestamps(self, list2):
    #     result = []
    #     for i in range(len(list2)):
    #         result.extend([list2[i]*self.elements_per_folders[i]])  # Repeat the timestamp list2[i] times
    #     return result

    def img_bulk(self):
        """
        Yields numpy array of images from imgbuffer between start and enddate
        until all images have been read.

        Returns
        -------
        img_stack_dict : dict[str, np.ndarray]
            stack of daily images for each variable
        startdate : datetime.datetime
            date of first image in stack
        enddate : datetime.datetime
            date of last image in stack
        datetimestack : np.ndarray
            array of the timestamps of each image
        jd_stack : np.ndarray or None
            None if all observations in an image have the same
            observation timestamp. Otherwise it gives the julian date
            of each observation in img_stack_dict

        Yields
        ------
        tuple[dict, datetime, np.ndarray or None]
        """

        timestamps = self.imgin.tstamps_for_daterange(
            self.startdate, self.enddate)

        element_per_folder_multipliers = []
        for i in range(len(timestamps)):
            # if self.elements_per_folders[i] == 4:
            #     d = 2
            element_per_folder_multipliers.extend([timestamps[i]] * self.elements_per_folders[i])
        timestamps = element_per_folder_multipliers

        # if self.overpass == 'BOTH':
        #     timestamps = [item for item in timestamps for _ in range(2)]
        # else:
        #     pass
        for i, dates in enumerate(idx_chunks(pd.DatetimeIndex(timestamps),
                                             self.imgbuffer)):

            # Need to temporarily remove grids as they cannot be pickled for MP
            target_grid = self.target_grid
            input_grid = self.input_grid
            self.target_grid = None
            self.input_grid = None

            ITER_KWARGS = {'date': dates}
            results = parallel_process(
                self._read_image,
                ITER_KWARGS=ITER_KWARGS,
                STATIC_KWARGS={'target_grid': target_grid,
                               'input_grid': input_grid},
                show_progress_bars=False,
                log_path=os.path.join(self.outputpath, '000_log'),
                log_filename=self.log_filename,
                loglevel="INFO",
                logger_name='img2ts',
                ignore_errors=self.ignore_errors,
                n_proc=self.n_proc,
                backend=self.backend,
            )

            img_dict = {}
            timestamps = np.array([])

            while (results is not None) and len(results) > 0:
                img, orthogonal = results.pop(0)

                for k, v in img.data.items():
                    if k not in img_dict:
                        img_dict[k] = []
                    img_dict[k].append(v)

                if self.orthogonal is None:
                    self.orthogonal = orthogonal
                if self.timekey is None:
                    self.timekey = img.timekey

                timestamps = np.append(timestamps, img.timestamp)

            del results, ITER_KWARGS

            order = np.argsort(timestamps)
            timestamps = timestamps[order]
            img_dict = {k: np.ma.vstack(v)[order] for k, v in img_dict.items()}

            # Add the previously removed grids back
            self.target_grid = target_grid
            self.input_grid = input_grid

            yield (img_dict, timestamps)

