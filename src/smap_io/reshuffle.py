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
Module for a command line interface to convert the SMAP data into a
time series format using the repurpose package
'''

import os
import shutil
import sys
import argparse
from datetime import datetime

import yaml
from repurpose.img2ts import Img2Ts
from smap_io.grid import EASE36CellGrid
from smap_io.interface import SPL3SMP_Ds, organize_smap_files
from smap_io.misc import get_first_last_day_images, read_yaml_from_folder
import pandas as pd


def extend_ts(img_path, ts_path):
    """
    Append new image data to an existing time series record.
    This will use the last_day from summary.yml in the time series
    directory to decide which date the update should start from and
    the available image directories to decide how many images can be
    appended.

    Parameters
    ----------
    img_path: str
        Path where the annual folders containing downloaded SMOS L2 images
        are stored
    ts_path: str
        Path where the converted time series (initially created using the
        reshuffle / swath2ts command) are stored.

    """

    out_file = os.path.join(ts_path, f"overview.yml")
    if not os.path.isfile(out_file):
        raise ValueError("No overview.yml found in the time series directory."
                         "Please use reshuffle / swath2ts for initial time "
                         f"series setup or provide overview.yml in {ts_path}.")

    props = read_yaml_from_folder(ts_path)
    startdate = pd.to_datetime(props['last_day']).to_pydatetime()
    _, last_day = get_first_last_day_images(img_path)

    if startdate is None or last_day is None:
        raise ValueError("No start and/or end date provided.")

    startdate = pd.to_datetime(startdate).to_pydatetime()
    last_day = pd.to_datetime(last_day).to_pydatetime()
    organize_smap_files(img_path, start_date=startdate, end_date=last_day)
    img_path_temp = os.path.join(img_path, "temp")
    if startdate < last_day:

        try:
            reshuffle(
                img_path_temp,
                ts_path,
                startdate,
                last_day,
                props['parameters'],
                time_key="tb_time_seconds",
                grid=EASE36CellGrid(only_land=True),
                overpass="BOTH",
                var_overpass_str=True)

            props[
                'comment'] = ("DO NOT CHANGE THIS FILE MANUALLY! Required for "
                              "data update.")
            props['last_day'] = str(last_day)
            props['last_update'] = str(datetime.now())

            # Ensure 'comment' is the first key when writing
            ordered_props = {
                'comment': props['comment'],
                'last_day': props['last_day'],
                'last_update': props['last_update'],
                # add any other props here in desired order
            }

            with open(out_file, 'w') as f:
                yaml.dump(ordered_props, f, default_flow_style=False,
                          sort_keys=False)
        except Exception as e:
            pass

        shutil.rmtree(img_path_temp)
    else:
        print(f"No extension required From: {startdate} To: {last_day}")


def reshuffle(input_root,
              outputpath,
              startdate,
              enddate,
              parameters,
              imgbuffer=200,
              time_key='tb_time_seconds',
              ignore_failed_reads=False,
              **ds_kwargs):
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
        If the version data does not contain multiple overpasses, this must
        be None
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
    time_key: str, optional (default: 'tb_time_seconds')
        Time attribute key in the input files.
    """
    if 'grid' not in ds_kwargs.keys():
        ds_kwargs['grid'] = EASE36CellGrid()
    ds_kwargs['parameter'] = parameters
    ds_kwargs['flatten'] = True

    input_dataset = SPL3SMP_Ds(input_root, time_key=time_key, **ds_kwargs)

    # If the output folder doesn't exist, create it
    if not os.path.exists(outputpath):
        os.makedirs(outputpath)

    # get time series attributes from first day of data.
    print(startdate)
    data = input_dataset.read(startdate)

    # Define the input grid, applying user-specified subgrid or using the
    # default
    input_grid = ds_kwargs['grid'].cut() if \
        isinstance(ds_kwargs['grid'], EASE36CellGrid) else ds_kwargs['grid']

    reshuffler = Img2Ts(
        input_dataset=input_dataset,
        outputpath=outputpath,
        startdate=startdate,
        enddate=enddate,
        input_grid=input_grid,
        imgbuffer=imgbuffer,
        # Buffer size, defines how many images are processed at a time
        cellsize_lat=5.0,  # Default latitude resolution for output grid
        cellsize_lon=5.0,  # Default longitude resolution for output grid
        global_attr=None,  # Optional global attributes
        ts_attributes=data.metadata,  # Metadata for time-series
        time_units='seconds since 2000-01-01 12:00:00',  # Time unit format
        # Specifies AM/PM/BOTH overpass filtering
        ignore_errors=ignore_failed_reads # Ignore failed reads
    )

    reshuffler.calc()


def mkdate(datestring):
    if len(datestring) == 10:
        return datetime.strptime(datestring, '%Y-%m-%d')
    if len(datestring) == 16:
        return datetime.strptime(datestring, '%Y-%m-%dT%H:%M')


def str2bool(val):
    if val in ["True", "true", "t", "T", "1"]:
        return True
    else:
        return False


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
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Convert SMAP data into time series format.")
    parser.add_argument(
        "dataset_root",
        help='Root of local filesystem where the data is stored.')
    parser.add_argument(
        "timeseries_root",
        help='Root of local filesystem where the timeseries should be stored.')
    parser.add_argument(
        "start",
        type=mkdate,
        help=("Startdate. Either in format YYYY-MM-DD or YYYY-MM-DDTHH:MM."))
    parser.add_argument(
        "end",
        type=mkdate,
        help=("Enddate. Either in format YYYY-MM-DD or YYYY-MM-DDTHH:MM."))
    parser.add_argument(
        "parameters",
        metavar="parameters",
        nargs="+",
        help=("Parameters to convert as strings as in the downloaded file"
              "e.g. soil_moisture soil_moisture_error"))
    parser.add_argument(
        "--time_key",
        metavar="time_key",
        default="tb_time_seconds",
        type=str,
        help=("Time_key for non-orthogonal time series format"))
    parser.add_argument(
        "--overpass",
        choices=['AM', 'PM', 'BOTH'],
        type=str,
        default='AM',
        help=("Select 'PM' for the descending overpass or 'AM' "
              "for the ascending one. Only necessary if dataset "
              "contains multiple overpasses. Default: 'AM'"))
    parser.add_argument(
        "--var_overpass_str",
        type=str2bool,
        default="False",
        help=(
            "Append overpass indicator to the reshuffled variables. "
            "E.g. Soil Moisture will be called soil_moisture_pm and "
            "soil_moisture_am instead "
            "of soil_moisture. Default: False"))
    parser.add_argument(
        "--crid",
        type=int,
        default=None,
        help='Composite Release ID. Reshuffle only files with this ID.'
             'See also https://nsidc.org/data/smap/data_versions#CRID '
             'If not specified, all files in the dataset_root directory are '
             'used. Default: None'
    )
    parser.add_argument(
        "--bbox",
        type=float,
        default=None,
        nargs=4,
        help=("min_lon min_lat max_lon max_lat. "
              "Bounding Box (lower left and upper right corner) "
              "of subset area of global images to reshuffle (WGS84). "
              "Default: None")),
    parser.add_argument(
        "--land_points",
        type=str2bool,
        default="False",
        help=("Set True to convert only land points as defined"
              " in the GLDAS land mask (faster and less/smaller files)")),
    parser.add_argument(
        "--imgbuffer",
        type=int,
        default=100,
        help=("How many images to read at once. Bigger numbers make the "
              "conversion faster but consume more memory. Default: 100."))

    args = parser.parse_args(args)
    # set defaults that can not be handled by argparse

    print(
        "Converting images in {ds_root} (ID:{crid}) from {start} to {end} to "
        "TS into folder {ts_root}."
        .format(
            ds_root=args.dataset_root,
            crid=args.crid if args.crid is not None else 'not specified',
            start=args.start.isoformat(),
            end=args.end.isoformat(),
            ts_root=args.timeseries_root))
    return args


def main(args):
    args = parse_args(args)

    grid = EASE36CellGrid(only_land=True)
    reshuffle(args.dataset_root,
              args.timeseries_root,
              args.start,
              args.end,
              args.parameters,
              time_key=args.time_key,
              grid=grid,
              overpass=args.overpass, )

def run():
    main(sys.argv[1:])


if __name__ == '__main__':
    grid = EASE36CellGrid(only_land=True)
    reshuffle("/home/tunterho/Projects/smap_test_download_data/temp",
              "/home/tunterho/smap_io/data/output009/AM_PM",
              datetime(2025, 9, 29, 23, 59, 59),
              datetime(2025, 11, 12, 0, 0, 0),


              ["soil_moisture", 'soil_moisture_error',
               'tb_time_seconds'],
              time_key='tb_time_seconds',)


