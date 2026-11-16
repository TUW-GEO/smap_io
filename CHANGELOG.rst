=========
Changelog
=========

Unreleased
==========
- If multiple (re-processed) files exist for a day, always use the latest
  one (highest CRID, then highest file counter), both when reading images and
  when organizing files for reshuffling (``select_latest_file``)
- ``update_ts`` / ``extend_ts`` starts on the day after the last day in the
  time series (the last day was appended twice before), keeps the
  ``parameters`` in ``overview.yml`` and no longer silently ignores errors
- ``smap_l3 reshuffle`` refuses to write into a directory that already
  contains time series files (it would append duplicate data)
- Add missing dependencies ``click``, ``pyyaml``, ``xarray``

Version 0.8.1
=============
- Bugfix smap l3 timeseries reader extension reader

Version 0.8
===========
- Add new smap l3 timeseries extension reader

Version 0.7
===========
- Docker Update

Version 0.6
===========
- New reader for GriddedNcIndexedRaggedTs timeseries format for SMAP-L3
  version 9 data
- Add option to create a timeseries containing both ascending and descending
  overpasses

Version 0.5
===========
- Add support to download all smap products and test actual download
- Allow reshuffling land points only (SPL3SMP)
- Allow reshuffling points in bounding box only (SPL3SMP)
- Testdata module is now using GitLFS and hosted at TUW
- Meta package follows pyscaffold 4 standards, yapf formatting added

Version 0.4
===========
- Switch to new pyscaffold structure
- Add support for SMAP L3 v6 data,
- Remove download support for v4 and v5 (decommissioned), reading still possible.
- Add option to rename variables with orbit indicator during reading.

Version 0.3
===========

- Add test for download
- Update documentation
- Add kwargs to time series reader
- Add option for download checking
- Add CRID reading
- Name PM variables *_pm in time series
- Add download module
- Add SMAP L3 v4 and v5 support
- Update readme

Version 0.2
===========

- Add metadata from netCDF file to returned image.
- Add option to return data as 1D arrays.
- Add image to time series conversion and time series reading interface.

Version 0.1
===========

- Initial version with one dataset supported.
