"""
Tests for the download module of GLDAS.
"""
from unittest import mock
import os
from datetime import datetime
from smap_io.download import get_last_formatted_dir_in_dir
from smap_io.download import get_first_formatted_dir_in_dir
from smap_io.download import get_last_folder
from smap_io.download import get_first_folder
from smap_io.download import folder_get_first_last
from smap_io.download import dates_empty_folders
from unittest.mock import patch, call, MagicMock
from smap_io.download import (wget_download, wget_map_download, download,
                              get_start_date, parse_args, main)
from argparse import Namespace





def test_get_last_dir_in_dir():
    path = os.path.join(os.path.dirname(__file__),
                        'smap_io-test-data', 'SPL3SMP.006')
    last_dir = get_last_formatted_dir_in_dir(path, "{:%Y.%m.%d}")
    assert last_dir == '2020.04.02'


def test_get_first_dir_in_dir():
    path = os.path.join(os.path.dirname(__file__),
                        'smap_io-test-data', 'SPL3SMP.006')
    last_dir = get_first_formatted_dir_in_dir(path, "{:%Y.%m.%d}")
    assert last_dir == '2020.04.01'


def test_get_last_folder():
    path = os.path.join(os.path.dirname(__file__),
                        'smap_io-test-data', 'SPL3SMP.006')
    last = get_last_folder(path, ['{:%Y.%m.%d}'])
    last_should = os.path.join(path, "2020.04.02")
    assert last == last_should


def test_get_first_folder():
    path = os.path.join(os.path.dirname(__file__),
                        'smap_io-test-data', 'SPL3SMP.006')
    last = get_first_folder(path, ['{:%Y.%m.%d}'])
    last_should = os.path.join(path, "2020.04.01")
    assert last == last_should


def test_get_start_end():
    path = os.path.join(os.path.dirname(__file__),
                        'smap_io-test-data', 'SPL3SMP.006')
    start, end = folder_get_first_last(path)
    start_should = datetime(2020, 4, 1)
    end_should = datetime(2020, 4, 2)
    assert end == end_should
    assert start == start_should


def test_check_downloaded_data():
    path = os.path.join(os.path.dirname(__file__),
                        'smap_io-test-data', 'SPL3SMP.006')
    missing = dates_empty_folders(path)
    assert len(missing) == 0


@patch("os.makedirs")
@patch("subprocess.call")
def test_wget_download_basic(mock_subprocess, mock_makedirs):
    url = "http://example.com/file.txt"
    target = "/path/to/download/file.txt"

    # Call the function
    wget_download(url, target)

    # Expected command list
    expected_command = [
        "wget", url, "--retry-connrefused", "--no-check-certificate",
        "--auth-no-challenge", "on", "-O", target
    ]

    # Check that os.makedirs is called to create the target directory
    mock_makedirs.assert_called_once_with(os.path.split(target)[0])

    # Check that the subprocess.call is invoked with the correct command
    mock_subprocess.assert_called_once_with(" ".join(expected_command),
                                            shell=True)


@patch("os.makedirs")
@patch("subprocess.call")
def test_wget_download_with_authentication(mock_subprocess, mock_makedirs):
    url = "http://example.com/protected/file.txt"
    target = "/path/to/download/file.txt"
    username = "user"
    password = "pass"

    # Call the function
    wget_download(url, target, username=username, password=password)

    # Expected command list
    expected_command = [
        "wget", url, "--retry-connrefused", "--no-check-certificate",
        "--auth-no-challenge", "on", "-O", target,
        "--user=user", "--password=pass"
    ]

    mock_makedirs.assert_called_once_with(os.path.split(target)[0])
    mock_subprocess.assert_called_once_with(" ".join(expected_command),
                                            shell=True)


@patch("os.makedirs")
@patch("subprocess.call")
def test_wget_download_with_cookie(mock_subprocess, mock_makedirs):
    url = "http://example.com/file.txt"
    target = "/path/to/download/file.txt"
    cookie_file = "/path/to/cookies.txt"

    # Call the function with a cookie file
    wget_download(url, target, cookie_file=cookie_file)

    # Expected command list
    expected_command = [
        "wget", url, "--retry-connrefused", "--no-check-certificate",
        "--auth-no-challenge", "on", "-O", target,
        "--load-cookies", cookie_file,
        "--save-cookies", cookie_file,
        "--keep-session-cookies"
    ]

    mock_makedirs.assert_called_once_with(os.path.split(target)[0])
    mock_subprocess.assert_called_once_with(" ".join(expected_command),
                                            shell=True)


@patch("os.makedirs")
@patch("subprocess.call")
def test_wget_download_recursive(mock_subprocess, mock_makedirs):
    url = "http://example.com/folder"
    target = "/path/to/download"
    filetypes = ["pdf", "txt"]

    # Call the function with recursive download and filetypes
    wget_download(url, target, recursive=True, filetypes=filetypes)

    # Expected command list
    expected_command = [
        "wget", url, "--retry-connrefused", "--no-check-certificate",
        "--auth-no-challenge", "on", "-P", target, "-nd", "-np", "-r",
        "-A pdf,txt"
    ]

    # Ensure the target path is created
    mock_makedirs.assert_called_once_with(os.path.split(target)[0])

    # Check that subprocess.call is invoked with the full command
    mock_subprocess.assert_called_once_with(" ".join(expected_command),
                                            shell=True)


@patch("smap_io.download.check_dl")
@patch("smap_io.download.wget_download")
def test_wget_map_download_success(mock_wget_download, mock_check_dl):
    # Mock `check_dl` to return True, simulating a successful download
    mock_check_dl.return_value = True

    # Input variables
    url_target = ["http://example.com/file.txt", "/path/to/download/file.txt"]

    # Call the function
    wget_map_download(url_target)

    # Verify that `check_dl` is called once and `wget_download` is not called (because the download is already "successful")
    mock_check_dl.assert_called_once_with(url_target[1])
    mock_wget_download.assert_not_called()


@patch("smap_io.download.check_dl")
@patch("smap_io.download.wget_download")
def test_wget_map_download_retries(mock_wget_download, mock_check_dl):
    # Mock `check_dl` to fail the first 4 times and pass on the 5th attempt
    mock_check_dl.side_effect = [False, False, False, False, True]

    # Input variables
    url_target = ["http://example.com/file.txt", "/path/to/download/file.txt"]

    # Call the function
    wget_map_download(url_target)

    # Verify `check_dl` was called 5 times (once per retry attempt)
    assert mock_check_dl.call_count == 5

    # Verify `wget_download` was called 4 times (since the download succeeded on the 5th `check_dl`)
    assert mock_wget_download.call_count == 4

    # Verify the final calls to the mocked functions
    mock_wget_download.assert_has_calls([
                                            call(
                                                url_target[0],
                                                url_target[1],
                                                username=None,
                                                password=None,
                                                cookie_file=None,
                                                recursive=False,
                                                filetypes=None,
                                                robots_off=False
                                            )
                                        ] * 4)  # Called 4 times with the same arguments





@patch("smap_io.download.wget_map_download")
def test_download_single_process(mock_wget_map_download):
    # Mock a successful download
    mock_wget_map_download.return_value = True

    urls = ["http://example.com/file1.txt", "http://example.com/file2.txt"]
    targets = ["/path/to/file1.txt", "/path/to/file2.txt"]

    # Call the function in single process mode
    download(urls, targets, num_proc=1)

    # Verify that wget_map_download is called for each URL-target pair
    expected_calls = [
        call([urls[0], targets[0]], None, None, mock.ANY, False, None, False),
        call([urls[1], targets[1]], None, None, mock.ANY, False, None, False),
    ]
    mock_wget_map_download.assert_has_calls(expected_calls, any_order=False)




@patch("smap_io.download.wget_map_download")
def test_download_with_optional_parameters(mock_wget_map_download):
    # Mock a successful download
    mock_wget_map_download.return_value = True

    urls = ["http://example.com/file1.txt"]
    targets = ["/path/to/file1.txt"]

    # Call the function with optional parameters
    download(
        urls,
        targets,
        num_proc=1,
        username="user",
        password="pass",
        recursive=True,
        filetypes=["txt", "csv"],
        robots_off=True,
    )

    # Verify that wget_map_download is called with the correct arguments
    mock_wget_map_download.assert_called_once_with(
        [urls[0], targets[0]],
        "user",
        "pass",
        mock.ANY,  # cookie_file will be a temporary file, so we match with ANY
        True,  # recursive
        ["txt", "csv"],  # filetypes
        True,  # robots_off
    )


@patch("smap_io.download.Pool")
@patch("smap_io.download.wget_map_download")
def test_download_error_handling(mock_wget_map_download, mock_pool):
    # Mock the multiprocessing pool
    mock_pool_instance = MagicMock()
    mock_pool.return_value = mock_pool_instance

    urls = ["http://example.com/file1.txt", "http://example.com/file2.txt"]
    targets = ["/path/to/file1.txt", "/path/to/file2.txt"]

    # Mock wget_map_download to raise an exception for one URL
    def mock_download(*args):
        if args[0][0] == "http://example.com/file1.txt":
            raise Exception("Download failed")
        return True

    mock_wget_map_download.side_effect = mock_download

    # Call the function and ensure it runs in single-process mode
    download(urls, targets, num_proc=1)

    # Ensure the first URL raises an error while the second proceeds successfully
    expected_calls = [
        call([urls[0], targets[0]], None, None, mock.ANY, False, None, False),
        call([urls[1], targets[1]], None, None, mock.ANY, False, None, False),
    ]
    mock_wget_map_download.assert_has_calls(expected_calls, any_order=False)


@patch("smap_io.download.tempfile.NamedTemporaryFile")
@patch("smap_io.download.wget_map_download")
def test_download_creates_tempfile(mock_wget_map_download, mock_tempfile):
    # Mock the temporary file creation
    mock_temp_instance = MagicMock()
    mock_temp_instance.name = "/path/to/temp_cookie_file"
    mock_tempfile.return_value = mock_temp_instance

    urls = ["http://example.com/file1.txt"]
    targets = ["/path/to/file1.txt"]

    # Call the function
    download(urls, targets, num_proc=1)

    # Ensure the temporary file is created and passed to wget_map_download
    mock_tempfile.assert_called_once()
    mock_wget_map_download.assert_called_once_with(
        [urls[0], targets[0]],
        None,
        None,
        "/path/to/temp_cookie_file",
        False,
        None,
        False,
    )


def test_get_start_date_valid_product():
    # Test with a valid product that starts with "SPL3SMP"
    product = "SPL3SMP.001"
    expected_date = datetime(2015, 3, 31, 0)

    assert get_start_date(product) == expected_date


def test_get_start_date_invalid_product():
    # Test with a product that does not start with "SPL3SMP"
    product = "INVALID_PRODUCT"

    assert get_start_date(product) is None


def test_get_start_date_empty_string():
    # Test with an empty string
    product = ""

    assert get_start_date(product) is None

def test_get_start_date_partial_match():
    # Test with a string that includes "SPL3SMP" but does not start with it
    product = "123SPL3SMP"

    assert get_start_date(product) is None




@patch("smap_io.download.get_start_date")
@patch("smap_io.download.folder_get_first_last")
def test_parse_args_with_all_arguments(mock_folder_get_first_last,
                                       mock_get_start_date):
    mock_folder_get_first_last.return_value = (None, None)
    mock_get_start_date.return_value = datetime(2015, 3, 31)

    # Mock input arguments
    args = [
        "data",  # localroot
        "--start", "2023-01-01",
        "--end", "2023-01-31",
        "--product", "SPL4SMAU.004",
        "--filetypes", "h5", "nc", "txt",
        "--username", "user",
        "--password", "pass",
        "--n_proc", "4",
    ]

    # Call the function
    parsed_args = parse_args(args)

    # Expected result
    expected = Namespace(
        localroot="data",
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 31),
        product="SPL4SMAU.004",
        filetypes=["h5", "nc", "txt"],
        username="user",
        password="pass",
        n_proc=4,
        urlroot="https://n5eil01u.ecs.nsidc.org",
        urlsubdirs=["SMAP", "SPL4SMAU.004", "%Y.%m.%d"],
        localsubdirs=["%Y.%m.%d"],
    )

    assert parsed_args == expected


@patch("smap_io.download.get_start_date")
@patch("smap_io.download.folder_get_first_last")
def test_parse_args_with_minimum_arguments(mock_folder_get_first_last,
                                           mock_get_start_date):
    # Mock folder_get_first_last: no files found
    mock_folder_get_first_last.return_value = (None, None)
    mock_get_start_date.return_value = datetime(2015, 3, 31)

    # Mock input arguments
    args = ["data"]

    # Call the function
    parsed_args = parse_args(args)

    # Expected result
    expected = Namespace(
        localroot="data",
        start=mock_get_start_date.return_value,
        end=datetime.now(),
        product="SPL3SMP.008",  # Default product
        filetypes=["h5", "nc"],  # Default filetypes
        username=None,
        password=None,
        n_proc=1,  # Default processes
        urlroot="https://n5eil01u.ecs.nsidc.org",
        urlsubdirs=["SMAP", "SPL3SMP.008", "%Y.%m.%d"],
        localsubdirs=["%Y.%m.%d"],
    )

    assert parsed_args.localroot == expected.localroot
    assert parsed_args.start == expected.start
    assert parsed_args.product == expected.product
    assert parsed_args.filetypes == expected.filetypes
    assert parsed_args.username == expected.username
    assert parsed_args.password == expected.password
    assert parsed_args.n_proc == expected.n_proc
    assert parsed_args.urlroot == expected.urlroot
    assert parsed_args.urlsubdirs == expected.urlsubdirs
    assert parsed_args.localsubdirs == expected.localsubdirs


@patch("smap_io.download.get_start_date")
@patch("smap_io.download.folder_get_first_last")
def test_parse_args_with_folder_dates(mock_folder_get_first_last,
                                      mock_get_start_date):
    # Mock folder_get_first_last: last data date available
    mock_folder_get_first_last.return_value = (
        datetime(2022, 12, 25), datetime(2022, 12, 31))
    mock_get_start_date.return_value = datetime(2015, 3, 31)

    # Mock input arguments
    args = ["data"]

    # Call the function
    parsed_args = parse_args(args)

    # Expected results:
    # - start defaults to the last date in the folder
    # - end defaults to now()
    expected_start = datetime(2022, 12, 31)
    expected_end = datetime.now()

    assert parsed_args.start == expected_start
    assert isinstance(parsed_args.end,
                      datetime) and parsed_args.end.date() == expected_end.date()


@patch("smap_io.download.get_start_date")
@patch("smap_io.download.folder_get_first_last")
def test_parse_args_without_end_date(mock_folder_get_first_last,
                                     mock_get_start_date):
    mock_folder_get_first_last.return_value = (None, None)
    mock_get_start_date.return_value = datetime(2015, 3, 31)

    # Mock input arguments without an end date
    args = [
        "data",
        "--start", "2022-12-01",
    ]

    # Call the function
    parsed_args = parse_args(args)

    # Expect the default end date to be `datetime.now()`
    expected = datetime.now()

    assert isinstance(parsed_args.end, datetime)
    assert parsed_args.end.date() == expected.date()


@patch("smap_io.download.get_start_date")
@patch("smap_io.download.folder_get_first_last")
def test_parse_args_without_start_date(mock_folder_get_first_last,
                                       mock_get_start_date):
    # Mock folder_get_first_last to provide existing folder data
    mock_folder_get_first_last.return_value = (
        datetime(2022, 12, 25), datetime(2022, 12, 31))
    mock_get_start_date.return_value = datetime(2015, 3, 31)

    # Mock input arguments without a start date
    args = [
        "data",
        "--end", "2023-01-01",
    ]

    # Call the function
    parsed_args = parse_args(args)

    # Expect the default start date to be taken from folder_get_first_last
    expected_start = datetime(2022, 12, 31)

    assert parsed_args.start == expected_start
    assert parsed_args.end == datetime(2023, 1, 1)


@patch("smap_io.download.dates_empty_folders")
@patch("smap_io.download.download_by_dt")
@patch("smap_io.download.daily")
@patch("smap_io.download.parse_args")
def test_main_retries_three_times_and_aborts(mock_parse_args, mock_daily,
                                             mock_download_by_dt,
                                             mock_dates_empty_folders):
    # Mock `parse_args`
    mock_args = MagicMock()
    mock_args.start = datetime(2023, 1, 1)
    mock_args.end = datetime(2023, 1, 2)
    mock_args.localroot = "/path/to/local"
    mock_parse_args.return_value = mock_args

    # Mock `daily` to return 2 dates
    mock_daily.return_value = iter([
        datetime(2023, 1, 1),
        datetime(2023, 1, 2),
    ])

    # Mock `dates_empty_folders` to always return missing dates (to simulate failure to download)
    mock_dates_empty_folders.side_effect = [
        [datetime(2023, 1, 1), datetime(2023, 1, 2)],  # First attempt
        [datetime(2023, 1, 1), datetime(2023, 1, 2)],  # Second attempt
        [datetime(2023, 1, 1), datetime(2023, 1, 2)],  # Third (final) attempt
    ]

    # Call the main function
    main([])

    # Assertions
    # Assert `download_by_dt` is called 3 times (for 3 retries)
    assert mock_download_by_dt.call_count == 3

    # Assert `dates_empty_folders` is called after each retry to check missing dates
    assert mock_dates_empty_folders.call_count == 3

    # Assert `daily` is called once to generate the date range
    mock_daily.assert_called_once_with(mock_args.start, mock_args.end)


@patch("smap_io.download.dates_empty_folders")
@patch("smap_io.download.download_by_dt")
@patch("smap_io.download.daily")
@patch("smap_io.download.parse_args")
def test_main_some_dates_missing_after_retries(mock_parse_args, mock_daily,
                                               mock_download_by_dt,
                                               mock_dates_empty_folders):
    # Mock `parse_args`
    mock_args = MagicMock()
    mock_args.start = datetime(2023, 1, 1)
    mock_args.end = datetime(2023, 1, 3)
    mock_args.localroot = "/path/to/local"
    mock_parse_args.return_value = mock_args

    # Mock `daily` to return 3 dates
    mock_daily.return_value = iter([
        datetime(2023, 1, 1),
        datetime(2023, 1, 2),
        datetime(2023, 1, 3),
    ])

    # Mock `dates_empty_folders` to simulate some dates remain missing after retries
    mock_dates_empty_folders.side_effect = [
        [datetime(2023, 1, 1), datetime(2023, 1, 2)],  # First attempt
        [datetime(2023, 1, 2)],  # Second attempt
        [datetime(2023, 1, 2)],  # Third (final) attempt
    ]

    # Call the main function
    main([])

    # Assertions
    # Assert `download_by_dt` is called 3 times (for 3 retries)
    assert mock_download_by_dt.call_count == 3

    # Assert `dates_empty_folders` is called after each retry
    assert mock_dates_empty_folders.call_count == 3

    # Assert `daily` function is called once
    mock_daily.assert_called_once_with(mock_args.start, mock_args.end)


@patch("smap_io.download.dates_empty_folders")
@patch("smap_io.download.download_by_dt")
@patch("smap_io.download.parse_args")
def test_main_no_initial_dates_to_download(mock_parse_args,
                                           mock_download_by_dt,
                                           mock_dates_empty_folders):
    # Mock `parse_args`
    mock_args = MagicMock()
    mock_args.start = datetime(2023, 1, 1)
    mock_args.end = datetime(2023, 1, 1)
    mock_args.localroot = "/path/to/local"
    mock_parse_args.return_value = mock_args

    # Mock `daily` to return no dates
    mock_dates_empty_folders.return_value = []

    # Call the main function
    main([])