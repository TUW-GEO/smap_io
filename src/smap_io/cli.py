import click
from datetime import datetime, timedelta
import pandas as pd
import os
import yaml

from smap_io.download import (
    main as download_main
)
from smap_io.interface import (
    organize_smap_files,
    get_max_time_from_netcdfs
)
from smap_io.misc import read_yaml_from_folder, get_first_last_day_images

import shutil
from smap_io.reshuffle import (
    main as reshuffle,
    extend_ts
)


@click.group(short_help="SMAP L3 Command Line Programs", name="smap_l3")
def smap_l3():
    """Top-level SMAP L3 command group."""
    pass


# ----------------------------------------------------
# DOWNLOAD COMMAND
# ----------------------------------------------------
@click.command(
    "download",
    context_settings={'show_default': True},
    short_help="Download SMAP L3 data from NSIDC."
)
@click.option("--output", type=click.Path(writable=True), required=True)
@click.option("--time_start", "-s", type=str, default=None,
              help="Start date YYYY-MM-DD. Defaults to earliest available.")
@click.option("--time_end", "-e", type=str,
              default=datetime.today().strftime("%Y-%m-%d"),
              help="End date YYYY-MM-DD. Defaults to current date.")
@click.option("--short_name", type=str, default="SPL3SMP",
              help="SMAP product to download. Default: SPL3SMP")
@click.option("--filetypes", type=str, default="h5,nc",
              help="Comma-separated file extensions to download. Default: "
                   "h5,nc")
@click.option("--username", type=str, default=None,
              help="NSIDC Earthdata username")
@click.option("--password", type=str, default=None,
              help="NSIDC Earthdata password")
@click.option("--version", type=str, default="009",
              help="SMAP product version. Default: 009")
def cli_download(output, time_start, time_end, version, short_name, filetypes,
                 username, password):
    """
    Download SMAP L3 data into LOCALROOT directory.
    """
    out_path_temp = os.path.join(output, 'temp')
    if not os.path.exists(out_path_temp):
        os.makedirs(out_path_temp)
    args_list = ['--output', out_path_temp]

    if time_start:
        args_list += ["--time_start", time_start]
    if time_end:
        args_list += ["--time_end", time_end]

    args_list += ["--short_name", short_name, "--filetypes"] + filetypes.split(
        ",")
    args_list += ["--version", version]

    if username:
        args_list += ["--username", username]
    if password:
        args_list += ["--password", password]

    # Call original argparse-based download main function
    download_main(args_list)
    folders_in_temp = [f for f in os.listdir(out_path_temp) if
                       os.path.isdir(os.path.join(out_path_temp, f))]
    folders_in_temp.sort(key=lambda d: tuple(map(int, d.split('.'))))
    print(folders_in_temp)
    date_counter = 0
    for folder in folders_in_temp:
        date = datetime.strptime(folder, "%Y.%m.%d")
        print(date)
        year = date.year
        day_of_year = date.timetuple().tm_yday
        for filename in os.listdir(os.path.join(out_path_temp, folder)):
            if date_counter == 0:
                start_date = date
            date_counter += 1
            src_file = os.path.join(os.path.join(out_path_temp, folder),
                                    filename)
            dst_dir = os.path.join(output, str(year), str(day_of_year))

            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
                dst_file = os.path.join(os.path.join(dst_dir, filename))
            else:
                dst_file = os.path.join(os.path.join(dst_dir, filename))
            print(dst_dir)

            print(f"Moving: {filename}")
            # Only move if it's a file (not a subfolder)
            if os.path.isfile(src_file):
                shutil.move(src_file, dst_file)
                print(f"Moved: {filename}")
    props = {}
    props[
        'comment'] = ("DO NOT CHANGE THIS FILE MANUALLY! Required for data "
                      "update.")
    props['first_day'] = time_start
    props['last_day'] = time_end
    props['last_update'] = datetime.now().strftime("%Y-%m-%d")
    with open(os.path.join(output, "overview.yml"), "w") as f:
        yaml.dump(props, f, default_flow_style=False, sort_keys=False)
    shutil.rmtree(out_path_temp)


# ----------------------------------------------------
# UPDATE IMAGE COMMAND
# ----------------------------------------------------
@click.command(
    "update_img",
    context_settings={'show_default': True},
    short_help="Update existing SMAP download folder with new images."
)
@click.option("--output", type=click.Path(writable=True), required=True)
@click.option("--time_start", "-s", type=str, default=None,
              help="Start date YYYY-MM-DD. Defaults to earliest available.")
@click.option("--time_end", "-e", type=str, default=None,
              help="End date YYYY-MM-DD. Defaults to current date.")
@click.option("--short_name", type=str, default="SPL3SMP",
              help="SMAP product to download. Default: SPL3SMP")
@click.option("--filetypes", type=str, default="h5,nc",
              help="Comma-separated file extensions to download. Default: "
                   "h5,nc")
@click.option("--version", type=str, default="009", )
@click.option("--username", type=str, default=None,
              help="NSIDC Earthdata username")
@click.option("--password", type=str, default=None,
              help="NSIDC Earthdata password")
def cli_update_img(output, time_start, time_end, short_name, filetypes,
                   version, username, password):
    """
    Download SMAP L3 data into output directory.
    """
    update_overview = os.path.join(output, f"overview.yml")
    if not os.path.isfile(update_overview):
        raise ValueError("No overview.yml found in the time series directory."
                         "Please use reshuffle / swath2ts for initial time "
                         f"series setup or provide overview.yml in {output}.")

    out_path_temp = os.path.join(output, 'temp')
    if not os.path.exists(out_path_temp):
        os.makedirs(out_path_temp)
    args_list = ["--output", out_path_temp]
    print(f"WARNING: {output} is empty. Creating new folder for images.")

    props = read_yaml_from_folder(output)
    start = pd.to_datetime(props["last_day"]).to_pydatetime()
    next_day = start + timedelta(days=1)
    time_start = next_day.strftime("%Y-%m-%d")
    args_list += ['--time_start', time_start]
    time_end = datetime.today().strftime("%Y-%m-%d")
    args_list += ['--time_end', time_end]
    args_list += ["--version", "009"]

    print(f"Updating images in {output} since {time_start}")

    if username:
        args_list += ["--username", username]
    if password:
        args_list += ["--password", password]

    # Call original argparse-based download main function
    download_main(args_list)
    folders_in_temp = [f for f in os.listdir(out_path_temp) if
                       os.path.isdir(os.path.join(out_path_temp, f))]
    for folder in folders_in_temp:
        date = datetime.strptime(folder, "%Y.%m.%d")
        year = date.year
        day_of_year = date.timetuple().tm_yday
        for filename in os.listdir(os.path.join(out_path_temp, folder)):
            src_file = os.path.join(os.path.join(out_path_temp, folder),
                                    filename)
            dst_dir = os.path.join(output, str(year), str(day_of_year))

            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
                dst_file = os.path.join(os.path.join(dst_dir, filename))
            else:
                dst_file = os.path.join(os.path.join(dst_dir, filename))
            print(dst_dir)
            print(f"Moving: {filename}")
            # Only move if it's a file (not a subfolder)
            if os.path.isfile(src_file):
                shutil.move(src_file, dst_file)
                print(f"Moved: {filename}")
    shutil.rmtree(out_path_temp)
    _, last_day = get_first_last_day_images(output)
    props[
        'comment'] = ("DO NOT CHANGE THIS FILE MANUALLY! Required for data "
                      "update.")
    props["last_day"] = last_day
    props["last_update"] = datetime.today().strftime("%Y-%m-%d-%H:%M:%S")
    with open(update_overview, 'w') as outfile:
        yaml.dump(props, outfile, default_flow_style=False)


# ----------------------------------------------------
# RESHUFFLE COMMAND
# ----------------------------------------------------
@click.command(
    "reshuffle",
    context_settings={'show_default': True},
    short_help="Convert SMAP L3 images into time series."
)
@click.argument("img_path", type=click.Path(exists=True))
@click.argument("ts_path", type=click.Path(writable=True))
@click.argument("parameters", type=str)
@click.option("--time_key", type=str, default="tb_time_seconds")
@click.option("--overpass", type=click.Choice(["AM", "PM", "BOTH"]),
              default="BOTH",
              help="SMAP overpass to include.")
@click.option("--var_overpass_str", type=bool, default=True,
              help="Append _am/_pm to variable names if True.")
@click.option("--land_points", type=bool, default=False, )
def cli_reshuffle(img_path, ts_path, parameters, time_key,
                  overpass, var_overpass_str, land_points):
    """
    Convert SMAP L3 imagery to time series storage format.
    PARAMETERS should be a comma-separated list of variables.
    """
    # Organize SMAP files by date

    props = read_yaml_from_folder(img_path)
    start = pd.to_datetime(props["first_day"]).to_pydatetime()
    end = pd.to_datetime(props["last_day"]).to_pydatetime()
    organize_smap_files(img_path, start_date=start, end_date=end)
    print(f"Preparing to reshuffle SMAP images from {img_path} to {ts_path} "
          f"for dates {start} to {end} and variables {parameters}.")

    # Build argument list as strings exactly like CLI
    img_path_temp = os.path.join(img_path, "temp")
    params_list = [p.strip() for p in parameters.split(",")]
    print(params_list)
    args_list = [
        img_path_temp,
        ts_path,
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        *params_list,
        "--time_key",
        time_key,
        "--overpass",
        overpass,
        "--var_overpass_str",
        str(var_overpass_str),
        "--land_points",
        str(land_points)  # must be string for argparse
    ]

    print("Passing argument list to reshuffle:")
    print(args_list)

    # Call reshuffle with argument list
    reshuffle(args_list)
    last_date_of_ts = get_max_time_from_netcdfs(
        ts_path, time_var='time')
    print(f"Reshuffled data to {ts_path} with max time {last_date_of_ts}.")
    props_ts = {}
    props_ts[
        'comment'] = ("DO NOT CHANGE THIS FILE MANUALLY! Required for data "
                      "update.")
    props_ts['last_day'] = pd.to_datetime(last_date_of_ts).strftime("%Y-%m-%d")
    props_ts['last_update'] = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    print(params_list)
    props_ts['parameters'] = params_list

    with open(os.path.join(ts_path, "overview.yml"), "w") as f:
        yaml.dump(props_ts, f, default_flow_style=False, sort_keys=False)
    print(f"Reshuffled data to {ts_path} with max time {max}.")
    shutil.rmtree(img_path_temp)


# ----------------------------------------------------
# UPDATE TS COMMAND
# ----------------------------------------------------
@click.command(
    "update_ts",
    context_settings={'show_default': True},
    short_help="Extend existing SMAP L3 time series with new images."
)
@click.argument("img_path", type=click.Path(exists=True))
@click.argument("ts_path", type=click.Path(writable=True))
def cli_update_ts(img_path, ts_path):
    """
    Extend a locally existing SMAP L3 time series record.
    """
    extend_ts(img_path, ts_path)


# ----------------------------------------------------
# Add commands to the group
# ----------------------------------------------------
smap_l3.add_command(cli_download)
smap_l3.add_command(cli_update_img)
smap_l3.add_command(cli_reshuffle)
smap_l3.add_command(cli_update_ts)
