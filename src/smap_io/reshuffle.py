# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2016, TU Wien
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
Module for a command line interface to convert the SMAP data into a
time series format using the repurpose package
'''

import os
import sys
import argparse
import numpy as np
from datetime import datetime

from pygeogrids import BasicGrid

from repurpose.img2ts import Img2Ts
from ease_grid import EASE2_grid
from smap_io.interface import SPL3SMP_Ds
from smap_io.grid import EASE36CellGrid


def reshuffle(input_root, outputpath, startdate, enddate, parameters,
              imgbuffer=200, **ds_kwargs):
    """
    Reshuffle method applied to ERA-Interim data.

    Parameters
    ----------
    input_root: string
        input path where era interim data was downloaded
    outputpath : string
        Output path.
    startdate : datetime
        Start date.
    enddate : datetime
        End date.
    parameters: list
        parameters to read and convert
    overpass : str, optional (default: 'AM')
        Select 'AM' for the descending overpass or 'PM' for the ascending one.
        If the version data does not contain multiple overpasses, this must be None
    var_overpass_str : bool, optional (default: True)
        Append overpass indicator to the loaded variables. E.g. Soil Moisture
        will be called soil_moisture_pm and soil_moisture_am, and soil_moisture
        in all cases if this is set to False.
    crid : int, optional (default: None)
        Search for files with this Composite Release ID for reshuffling only.
        See also https://nsidc.org/data/smap/data_versions#CRID
    grid: pygeogrids.Cellgrid, optional (default: None)
        Subgrid to limit reading to.
    imgbuffer: int, optional (default: 50)
        How many images to read at once before writing time series.
    """
    if 'grid' not in ds_kwargs.keys():
        ds_kwargs['grid'] = EASE36CellGrid()
    ds_kwargs['parameter'] = parameters
    ds_kwargs['flatten'] = True

    input_dataset = SPL3SMP_Ds(input_root, **ds_kwargs)
    global_attr = {'product': 'SPL3SMP'}


    if not os.path.exists(outputpath):
        os.makedirs(outputpath)

    # get time series attributes from first day of data.
    data = input_dataset.read(startdate)
    ts_attributes = data.metadata

    # global_attr['overpass'] = getattr(input_dataset.fid, 'overpass')

    input_grid = ds_kwargs['grid'].cut() if isinstance(ds_kwargs['grid'], EASE36CellGrid) else ds_kwargs['grid']

    reshuffler = Img2Ts(input_dataset=input_dataset, outputpath=outputpath,
                        startdate=startdate, enddate=enddate, input_grid=input_grid,
                        imgbuffer=imgbuffer, cellsize_lat=5.0, cellsize_lon=5.0,
                        global_attr=global_attr, ts_attributes=ts_attributes)
    reshuffler.calc()


def mkdate(datestring):
    if len(datestring) == 10:
        return datetime.strptime(datestring, '%Y-%m-%d')
    if len(datestring) == 16:
        return datetime.strptime(datestring, '%Y-%m-%dT%H:%M')


def parse_args(args):
    """
    Parse command line parameters for conversion from image to time series.
    Parameters
    ----------
    args: list
        command line parameters as list of strings
    Returns
    ----------
    args : argparse.Namespace
        Parsed command line parameters
    """

    parser = argparse.ArgumentParser(
        description="Convert SMAP data into time series format.")
    parser.add_argument("dataset_root",
                        help='Root of local filesystem where the data is stored.')
    parser.add_argument("timeseries_root",
                        help='Root of local filesystem where the timeseries should be stored.')
    parser.add_argument("start", type=mkdate,
                        help=("Startdate. Either in format YYYY-MM-DD or YYYY-MM-DDTHH:MM."))
    parser.add_argument("end", type=mkdate,
                        help=("Enddate. Either in format YYYY-MM-DD or YYYY-MM-DDTHH:MM."))
    parser.add_argument("parameters", metavar="parameters",
                        nargs="+",
                        help=("Parameters to convert as strings as in the downloaded file"
                              "e.g. soil_moisture soil_moisture_error"))
    parser.add_argument("--overpass", type=str, default='AM',
                        help=("Select 'AM' for the descending overpass or 'AM' "
                              "for the ascending one. Only necessary if dataset "
                              "contains multiple overpasses. Default: 'AM'"))
    parser.add_argument("--var_overpass_str", type=bool, default=False,
                        help=("Append overpass indicator to the reshuffled variables. "
                              "E.g. Soil Moisture will be called soil_moisture_pm and soil_moisture_am instead "
                              "of soil_moisture. Default: False"))
    parser.add_argument("--crid", type=int, default=None,
                        help='Composite Release ID. Reshuffle only files with this ID.'
                             'See also https://nsidc.org/data/smap/data_versions#CRID '
                             'If not specified, all files in the dataset_root directory are used. Default: None')
    parser.add_argument("--bbox", type=float, default=None, nargs=4,
                        help=("min_lon min_lat max_lon max_lat. "
                              "Bounding Box (lower left and upper right corner) "
                              "of subset area of global images to reshuffle (WGS84). "
                              "Default: None"))
    parser.add_argument("--imgbuffer", type=int, default=100,
                        help=("How many images to read at once. Bigger numbers make the "
                              "conversion faster but consume more memory. Default: 100."))
    args = parser.parse_args(args)
    # set defaults that can not be handled by argparse

    print("Converting images in {ds_root} (ID:{crid}) from {start} to {end} to TS into folder {ts_root}."
          .format(ds_root=args.dataset_root,
                  crid=args.crid if args.crid is not None else 'not specified',
                  start=args.start.isoformat(),
                  end=args.end.isoformat(),
                  ts_root=args.timeseries_root))
    return args


def main(args):
    args = parse_args(args)

    if 'bbox' in args:
        grid = EASE36CellGrid(bbox=args.bbox)
    else:
        grid = None

    reshuffle(args.dataset_root,
              args.timeseries_root,
              args.start,
              args.end,
              args.parameters,
              grid=grid,
              overpass=None if args.overpass in ['False', 'false', 'none', 'None'] else args.overpass,
              var_overpass_str=args.var_overpass_str,
              crid=args.crid,
              imgbuffer=args.imgbuffer)


def run():
    main(sys.argv[1:])

if __name__ == '__main__':
    #run()
    from pygeogrids.netcdf import load_grid
    for overpass in ["AM", 'PM']:
        ds_root = "/home/wpreimes/shares/radar/Datapool/SMAP/01_raw/SPL3SMP_v6/"
        ts_root = f"/home/wpreimes/shares/radar/Projects/QA4SM_HR/07_data/SMAP_SPL3SMP_land_data/{overpass}"
        os.makedirs(ts_root, exist_ok=True)
        start = datetime(2015,3,31)
        end = datetime(2020,5,27)
        grid = load_grid("/home/wpreimes/shares/home/code/smap_io/src/_local_scripts/ease36_landgrid.nc")
        grid = EASE36CellGrid().subgrid_from_gpis(grid.activegpis)
        params = ["freeze_thaw_fraction", "retrieval_qual_flag", "soil_moisture", "soil_moisture_error",
                  "surface_flag", "surface_temperature", "vegetation_opacity", "vegetation_water_content"]
        reshuffle(ds_root, ts_root, start, end, params, overpass=overpass, grid=grid)