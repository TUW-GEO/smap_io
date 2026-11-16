# AGENTS.md — smap_io

Guide for coding agents (and humans) working on this repository.

> **Keep this file up to date.** Whenever you change behaviour, the CLI,
> data layout conventions, dependencies, tests or the deployment setup, or
> learn something non-obvious about this package (a pitfall, a bug, a
> verified assumption), update the relevant section of this file in the same
> change. Remove information that is no longer true. Note the date
> (YYYY-MM-DD) in the "Change log of this file" section at the bottom.

## What this package does

Reads NASA SMAP soil moisture data (mainly L3 passive, `SPL3SMP`, version 009
on the 36 km EASE2 grid, 406 x 964) and converts daily images to time series.
It is used by QA4SM: weekly Airflow jobs download new images and extend the
time series.

## Layout

- `src/smap_io/interface.py`: image readers (`SPL3SMP_Img`, `SPL3SMP_Ds`),
  time series readers (`SMAPTs` for OrthoMulti, `SMAPL3_V9Reader` for
  IndexedRagged, `ReaderWithExtension_SMAP` to concatenate base + extension
  record), file helpers (`parse_smap_filename`, `select_latest_file`,
  `organize_smap_files`, `get_max_time_from_netcdfs`, ...).
- `src/smap_io/reshuffle.py`: `reshuffle()` (image → time series via
  `repurpose.Img2Ts`), `extend_ts()` (append new days), argparse `main()`
  (`smap_repurpose` entry point).
- `src/smap_io/cli.py`: click group `smap_l3` with `download`, `update_img`,
  `reshuffle`, `update_ts`.
- `src/smap_io/download.py`: NSIDC / Earthdata (CMR) download.
- `src/smap_io/misc.py`: yml helpers, first/last image day from the folder
  structure.
- `src/smap_io/grid.py`: `EASE36CellGrid` (`only_land=True` uses
  `grids/ease36land.nc`).
- `tests/`: pytest; test images in `tests/smap_io-test-data/SPL3SMP.006`
  (2020-04-01 and 2020-04-02, CRID 16515).

## Data layout and conventions

- Image store: `<img_path>/<YYYY>/<DOY>/SMAP_L3_SM_P_YYYYMMDD_R<CRID>_<NNN>.h5`
  plus `<img_path>/overview.yml` (`first_day`, `last_day`, `last_update`).
- For reshuffling, `organize_smap_files` copies the files to
  `<img_path>/temp/YYYY.MM.DD/` (the layout `SPL3SMP_Ds` expects,
  `subpath_templ=('%Y.%m.%d',)`). The temp folder is wiped at the start and
  removed after reshuffling.
- **Multiple files per day:** NSIDC re-processes days and publishes new
  files with a higher file counter (`_002`, `_003`) or a higher CRID. Always
  use the latest: `select_latest_file` picks the max (CRID, counter).
  `SPL3SMP_Ds._build_filename` and `organize_smap_files(latest_only=True)`
  both use it. Old versions stay in the image store (the download does not
  delete them).
- Time series store (v9, `overpass='BOTH'`): pynetcf IndexedRagged cell files
  (`NNNN.nc`, 5° cells, land points only) + `grid.nc` + `overview.yml`
  (`last_day`, `last_update`, `parameters`). AM and PM are separate rows,
  told apart by the `Overpass` variable (1 = AM, 2 = PM). The time stamp is
  `tb_time_seconds` (seconds since 2000-01-01 12:00).
- The image reader masks values outside the variable's `valid_min` /
  `valid_max` to the fill value. For `soil_moisture` that's 0.02–0.5, so
  about 6–7 % of the raw values (mostly > 0.5) are dropped on purpose.
- QA4SM layout: base record `SMAP_L3/SMAP_V9_AM_PM/netcdf` (until
  2025-01-26) and extension `SMAP_L3/SMAP_V9_AM_PM-ext/{images,timeseries}`
  (from 2025-01-26), read together with `ReaderWithExtension_SMAP`.

## Important invariants and pitfalls

- **`repurpose.Img2Ts` always appends** to existing cell files (mode 'a'). Never
  reshuffle a period into a directory that already holds it, or it gets
  duplicated. `smap_l3 reshuffle` refuses a directory that already has cell
  files. To reprocess from scratch, use an empty directory.
- `extend_ts` starts on `last_day + 1` (from the ts `overview.yml`) and
  ends on the last image day. It must keep `parameters` in `overview.yml`,
  because the next update needs them.
- **Argument order:** `smap_l3 update_ts IMG_PATH TS_PATH` and
  `extend_ts(img_path, ts_path)`. Some other QA4SM packages (e.g. era5) use
  `update_ts TS_PATH --imgpath ...`. Swapped arguments now raise a
  `ValueError`.
- `overpass='BOTH'` uses module-level globals (`counter`,
  `overpass_state_AM`) to alternate AM/PM between consecutive reads of the
  same day. `tstamps_for_daterange` yields each day twice. A missing file
  fails in `_build_filename` before the toggle, so pairs stay in sync. The
  globals persist within a process, so the AM/PM read order can flip between
  calls. This is harmless because `Overpass` is set per read.
- `reshuffle()` reads the first *available* day in the range to get the
  metadata (the start day may be missing).
- History (found 2026-11-12): the Airflow DAG called
  `update_ts {ts_path} {img_path}` (swapped). `extend_ts` failed, and the
  shell `A && B || C` then ran a full `reshuffle` every week, appending the
  whole extension period again (about 23x duplicates in
  `SMAP_V9_AM_PM-ext/timeseries`). Superseded image versions also left stale
  near-duplicate rows. The values were otherwise correct: no observations
  were lost compared to the images.

## Deployment

- Airflow DAG: `qa4sm-airflow/dags/data_update/smap_update.py` (weekly). It
  runs `smap_l3 update_img`, then `smap_l3 update_ts IMG TS` if cell files
  exist, otherwise `smap_l3 reshuffle ...`. Docker image from `Dockerfile`
  (micromamba + `environment.yml` + `pip install .`).
- Keep `environment.yml` and `setup.cfg` `install_requires` in sync.

## Development

- Conda env: `smap_io` (`/home/wpreimes/miniforge3/envs/smap_io`), package
  installed in editable mode from `src/`.
- Tests: `python -m pytest tests -k "not env_download"` (about 1 min;
  `test_env_download` needs Earthdata credentials and network). Add
  `--no-cov -p no:cacheprovider` for quicker local runs.
- Source files use **CRLF** line endings. Keep them (don't convert files).
- Style: yapf (see `setup.cfg`), line length 79.
- Default PR target branch is `smap_l3_sm_v5`. `master` is the working branch.

## Change log of this file

- 2026-11-12: Created. Documented latest-file selection, duplicate-safe
  `extend_ts` / `reshuffle`, the DAG argument order bug and the data layout.
