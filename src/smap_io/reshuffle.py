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
from datetime import datetime

from img2ts import Img2Ts
from smap_io.grid import EASE36CellGrid
from interface import SPL3SMP_Ds


def reshuffle(input_root,
              outputpath,
              startdate,
              enddate,
              parameters,
              use_all_elements_per_folder,
              imgbuffer=200,
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
    exclude_missing_time_stamps_bool = ds_kwargs.get('exclude_missing_time_stamps')
    del ds_kwargs['exclude_missing_time_stamps']
    if 'grid' not in ds_kwargs.keys():
        ds_kwargs['grid'] = EASE36CellGrid()
    ds_kwargs['parameter'] = parameters
    ds_kwargs['flatten'] = True

    input_dataset = SPL3SMP_Ds(input_root, **ds_kwargs)
    # input_test = SPL3SMP_Ds(input_root, overpass='PM', var_overpass_str=False,**ds_kwargs)

    if not os.path.exists(outputpath):
        os.makedirs(outputpath)

    # get time series attributes from first day of data.
    data = input_dataset.read(startdate)
    # Get metadata attributes from the first day of data.

    # global_attr['overpass'] = getattr(input_dataset.fid, 'overpass')

    input_grid = ds_kwargs['grid'].cut() if \
        isinstance(ds_kwargs['grid'], EASE36CellGrid) else ds_kwargs['grid']

    time_stamps_per_day = count_elements_in_folders(input_root, startdate, enddate)
    if use_all_elements_per_folder:
        if ds_kwargs['overpass'] == 'BOTH':
            for i in range(len(time_stamps_per_day)):
                time_stamps_per_day[i] = time_stamps_per_day[i] * 2
            else:
                pass
    else:
        if ds_kwargs['overpass'] == 'BOTH':
            time_stamps_per_day = [2] * len(time_stamps_per_day)
        else:
            time_stamps_per_day = [1] * len(time_stamps_per_day)


    reshuffler = Img2Ts(
        input_dataset=input_dataset,
        outputpath=outputpath,
        startdate=startdate,
        enddate=enddate,
        input_grid=input_grid,
        imgbuffer=imgbuffer,
        cellsize_lat=5.0,  # Default cellsize for latitude
        cellsize_lon=5.0,  # Default cellsize for longitude
        global_attr=None,
        ts_attributes=data.metadata,
        time_units='seconds since 2000-01-01 12:00:00',
        exclude_missing_time_stamps=exclude_missing_time_stamps_bool,
        overpass=ds_kwargs['overpass'],
        elements_per_folders=time_stamps_per_day
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

# def count_elements_in_folders(directory):
#     element_counts = []  # Initialize an empty list to store element counts
#
#     # List all folders in the given directory
#     for foldername in os.listdir(directory):
#         folder_path = os.path.join(directory, foldername)
#
#         # Check if it's a directory
#         if os.path.isdir(folder_path):
#             # Get the list of all elements in the folder and append the count to the list
#             elements = os.listdir(folder_path)
#             element_counts.append((foldername, len(elements)))  # Use a tuple to store both
#
#     # Sort the list of tuples by the folder name (first element of the tuple)
#     element_counts = sorted(element_counts, key=lambda x: x[0])
#
#     # Extract just the element counts (second element of each tuple)
#     # element_counts = [count for _, count in element_counts]
#
#     return element_counts


def count_elements_in_folders(directory, start_date, end_date):
    element_counts = []  # Initialize an empty list to store element counts

    # List all folders in the given directory
    for foldername in os.listdir(directory):
        folder_path = os.path.join(directory, foldername)

        # Check if it's a directory
        if os.path.isdir(folder_path):
            try:
                # Assuming folder names are in "YYYY-MM-DD" format
                folder_date = datetime.strptime(foldername, "%Y.%m.%d")

                # Check if the folder date is within the specified range
                if start_date <= folder_date <= end_date:
                    # Get the list of all elements in the folder and append the count to the list
                    elements = os.listdir(folder_path)
                    element_counts.append((foldername, len(elements)))  # Use a tuple to store both
            except ValueError:
                # Skip folders with names that can't be parsed as dates
                continue

    # Sort the list of tuples by the folder name (first element of the tuple)
    element_counts = sorted(element_counts, key=lambda x: x[0])

    # Extract just the element counts (second element of each tuple)
    element_counts = [count for _, count in element_counts]

    return element_counts

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
        'use_all_elements_per_folder',
        type=bool,
        default=False,
        help=("If True, use all elements in folder for time series.")
    )
    parser.add_argument(
        "--overpass",
        choices=['AM', 'PM', 'both'],
        type=str,
        default='AM',
        help=("Select 'PM' for the descending overpass or 'AM' "
              "for the ascending one. Only necessary if dataset "
              "contains multiple overpasses. Default: 'AM'"))
    parser.add_argument(
        "--exclude_missing_time_stamps",
        choices=[True, False],
        type=bool,
        default=True,
        help=("Decide if timestamps with no Observations should be excluded from the time series"))
    parser.add_argument(
        "--var_overpass_str",
        type=str2bool,
        default="False",
        help=(
            "Append overpass indicator to the reshuffled variables. "
            "E.g. Soil Moisture will be called soil_moisture_pm and soil_moisture_am instead "
            "of soil_moisture. Default: False"))
    parser.add_argument(
        "--crid",
        type=int,
        default=None,
        help='Composite Release ID. Reshuffle only files with this ID.'
        'See also https://nsidc.org/data/smap/data_versions#CRID '
        'If not specified, all files in the dataset_root directory are used. Default: None'
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
        "Converting images in {ds_root} (ID:{crid}) from {start} to {end} to TS into folder {ts_root}."
        .format(
            ds_root=args.dataset_root,
            crid=args.crid if args.crid is not None else 'not specified',
            start=args.start.isoformat(),
            end=args.end.isoformat(),
            ts_root=args.timeseries_root))
    return args


def main(args):
    args = parse_args(args)

    grid = EASE36CellGrid(
        bbox=args.bbox if 'bbox' in args else None,
        only_land=True if args.land_points else False)

    reshuffle(
        args.dataset_root,
        args.timeseries_root,
        args.start,
        args.end,
        args.parameters,
        args.use_all_elements_per_folder,
        grid=grid,
        overpass=None if args.overpass in ['False', 'false', 'none', 'None']
        else args.overpass,
        var_overpass_str=args.var_overpass_str,
        crid=args.crid,
        imgbuffer=args.imgbuffer)


def run():
    main(sys.argv[1:])


if __name__ == '__main__':
    grid = EASE36CellGrid(only_land=True)
    reshuffle("/home/tunterho/smap_io/data/input",
              "/home/tunterho/smap_io/data/output009/AM_PM",

              datetime(2015, 3, 31, 0, 0, 0),
              datetime(2025, 1, 26, 23, 59, 59),

              ["soil_moisture", 'soil_moisture_error', "retrieval_qual_flag", "freeze_thaw_fraction", "surface_flag", "surface_temperature", "vegetation_opacity", "vegetation_water_content", "landcover_class", 'static_water_body_fraction', 'tb_time_seconds'],
              False,
              grid=grid,
              overpass='BOTH',
              exclude_missing_time_stamps=True
              )

    #from smap_io.interface import SMAPTs

    #ts_reader = SMAPTs("/tmp/test", ioclass_kws={'read_bulk': True})
    #ts = ts_reader.read(15, 45)  # lon, lat

