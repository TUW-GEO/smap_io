"""
Tests for selecting the latest file version per day and for extending
existing time series without duplicating data.
"""
import os
import glob
import shutil
from datetime import datetime

import h5py
import netCDF4
import numpy as np
import numpy.testing as nptest
import pytest
import yaml
from click.testing import CliRunner

from smap_io.interface import (
    SPL3SMP_Ds, SMAPL3_V9Reader, select_latest_file, parse_smap_filename,
    organize_smap_files)
from smap_io.reshuffle import extend_ts
from smap_io.cli import cli_reshuffle

TESTDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "smap_io-test-data", "SPL3SMP.006")
F1 = os.path.join(TESTDATA, "2020.04.01", "SMAP_L3_SM_P_20200401_R16515_001.h5")
F2 = os.path.join(TESTDATA, "2020.04.02", "SMAP_L3_SM_P_20200402_R16515_001.h5")
PARAMS = ["soil_moisture", "soil_moisture_error", "tb_time_seconds"]


def _copy_with_value(src, dst, value=None, idx=(76, 466)):
    """Copy a test file, optionally overwrite one AM soil moisture value."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    if value is not None:
        with h5py.File(dst, "r+") as f:
            f["Soil_Moisture_Retrieval_Data_AM/soil_moisture"][idx] = value


def test_parse_smap_filename():
    p = parse_smap_filename("/some/path/SMAP_L3_SM_P_20251018_R19240_002.h5")
    assert p == {"date": "20251018", "crid": 19240, "counter": 2}
    assert parse_smap_filename("grid.nc") is None


@pytest.mark.parametrize("files,expected", [
    (["SMAP_L3_SM_P_20260401_R19240_001.h5",
      "SMAP_L3_SM_P_20260401_R19240_003.h5",
      "SMAP_L3_SM_P_20260401_R19240_002.h5"],
     "SMAP_L3_SM_P_20260401_R19240_003.h5"),
    # a higher CRID wins over a higher counter
    (["SMAP_L3_SM_P_20260401_R19240_004.h5",
      "SMAP_L3_SM_P_20260401_R19241_001.h5"],
     "SMAP_L3_SM_P_20260401_R19241_001.h5"),
    # numeric, not lexical comparison of the counter
    (["SMAP_L3_SM_P_20260401_R19240_9.h5",
      "SMAP_L3_SM_P_20260401_R19240_10.h5"],
     "SMAP_L3_SM_P_20260401_R19240_10.h5"),
    (["SMAP_L3_SM_P_20260401_R19240_001.h5"],
     "SMAP_L3_SM_P_20260401_R19240_001.h5"),
])
def test_select_latest_file(files, expected):
    assert select_latest_file(files) == expected
    with_dir = [os.path.join("/a", "b", f) for f in files]
    assert select_latest_file(with_dir) == os.path.join("/a", "b", expected)


def test_select_latest_file_empty():
    with pytest.raises(ValueError):
        select_latest_file([])


def test_ds_reads_latest_file(tmp_path):
    day = tmp_path / "2020.04.01"
    _copy_with_value(F1, str(day / "SMAP_L3_SM_P_20200401_R16515_001.h5"))
    _copy_with_value(F1, str(day / "SMAP_L3_SM_P_20200401_R16515_002.h5"),
                     value=0.4)
    ds = SPL3SMP_Ds(str(tmp_path), overpass="AM", var_overpass_str=False)
    img = ds.read(datetime(2020, 4, 1))
    nptest.assert_almost_equal(img.data["soil_moisture"][76, 466], 0.4, 5)

    # a newer CRID is preferred over a higher counter
    _copy_with_value(F1, str(day / "SMAP_L3_SM_P_20200401_R16516_001.h5"),
                     value=0.3)
    img = ds.read(datetime(2020, 4, 1))
    nptest.assert_almost_equal(img.data["soil_moisture"][76, 466], 0.3, 5)


def test_organize_smap_files_latest_only(tmp_path):
    img = tmp_path / "img"
    _copy_with_value(F1, str(img / "2020" / "92" /
                             "SMAP_L3_SM_P_20200401_R16515_001.h5"))
    _copy_with_value(F1, str(img / "2020" / "92" /
                             "SMAP_L3_SM_P_20200401_R16515_002.h5"))
    _copy_with_value(F2, str(img / "2020" / "93" /
                             "SMAP_L3_SM_P_20200402_R16515_001.h5"))
    # leftover from a crashed run must not survive
    _copy_with_value(F1, str(img / "temp" / "2020.04.01" /
                             "SMAP_L3_SM_P_20200401_R16515_000.h5"))

    organize_smap_files(str(img), start_date="2020-04-01",
                        end_date="2020-04-02")
    assert sorted(os.listdir(img / "temp" / "2020.04.01")) == \
        ["SMAP_L3_SM_P_20200401_R16515_002.h5"]
    assert sorted(os.listdir(img / "temp" / "2020.04.02")) == \
        ["SMAP_L3_SM_P_20200402_R16515_001.h5"]

    organize_smap_files(str(img), start_date="2020-04-01",
                        end_date="2020-04-01", latest_only=False)
    assert sorted(os.listdir(img / "temp" / "2020.04.01")) == \
        ["SMAP_L3_SM_P_20200401_R16515_001.h5",
         "SMAP_L3_SM_P_20200401_R16515_002.h5"]


def _n_rows_and_unique(ts_path):
    """Total number of rows and unique (location, time, overpass) rows."""
    n, n_unique = 0, 0
    for f in glob.glob(os.path.join(ts_path, "[0-9]*.nc")):
        with netCDF4.Dataset(f) as ds:
            ds.set_auto_mask(False)
            li = ds["locationIndex"][:]
            t = ds["time"][:]
            op = ds["Overpass"][:]
        n += li.size
        n_unique += len(set(zip(li, t, op)))
    return n, n_unique


def test_reshuffle_then_extend_no_duplicates(tmp_path):
    img = tmp_path / "img"
    ts = tmp_path / "ts"
    _copy_with_value(F1, str(img / "2020" / "92" /
                             "SMAP_L3_SM_P_20200401_R16515_001.h5"))
    with open(img / "overview.yml", "w") as f:
        yaml.dump({"first_day": "2020-04-01", "last_day": "2020-04-01"}, f)

    # Initial time series, first day only
    runner = CliRunner()
    res = runner.invoke(cli_reshuffle, [str(img), str(ts), ",".join(PARAMS)],
                        catch_exceptions=False)
    assert res.exit_code == 0, res.output
    with open(ts / "overview.yml") as f:
        props = yaml.safe_load(f)
    assert props["last_day"] == "2020-04-01"
    assert props["parameters"] == PARAMS
    n_day1, _ = _n_rows_and_unique(str(ts))

    # Reshuffling into an existing record is refused (would duplicate data)
    res = runner.invoke(cli_reshuffle, [str(img), str(ts), ",".join(PARAMS)])
    assert res.exit_code != 0
    assert "already contains time series" in res.output
    assert _n_rows_and_unique(str(ts))[0] == n_day1

    # Swapped arguments raise a clear error and do not touch the data
    with pytest.raises(ValueError):
        extend_ts(str(ts), str(img))
    assert _n_rows_and_unique(str(ts))[0] == n_day1

    # New image arrives (two versions); extend appends only the new day
    _copy_with_value(F2, str(img / "2020" / "93" /
                             "SMAP_L3_SM_P_20200402_R16515_001.h5"))
    _copy_with_value(F2, str(img / "2020" / "93" /
                             "SMAP_L3_SM_P_20200402_R16515_002.h5"))
    extend_ts(str(img), str(ts))
    assert not os.path.exists(img / "temp")

    with open(ts / "overview.yml") as f:
        props = yaml.safe_load(f)
    assert props["last_day"] == "2020-04-02"
    assert props["parameters"] == PARAMS  # kept for the next update

    n, n_unique = _n_rows_and_unique(str(ts))
    assert n == n_unique
    assert n > n_day1

    # Running the update again does not change anything
    extend_ts(str(img), str(ts))
    assert _n_rows_and_unique(str(ts)) == (n, n_unique)

    reader = SMAPL3_V9Reader(str(ts), ioclass_kws={"read_bulk": True})
    data = reader.read(-2.8, 55.4)
    reader.close()
    assert not data.index.duplicated().any()
    nptest.assert_almost_equal(
        np.sort(data["soil_moisture"].values),
        np.sort(np.array([0.255842, 0.246838, 0.262245], dtype=np.float32)),
        decimal=6)
