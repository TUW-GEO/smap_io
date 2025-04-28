"""
Tests for the download module of GLDAS.
"""
import os
from datetime import datetime

from smap_io.download import get_last_formatted_dir_in_dir
from smap_io.download import get_first_formatted_dir_in_dir
from smap_io.download import get_last_folder
from smap_io.download import get_first_folder
from smap_io.download import folder_get_first_last
from smap_io.download import dates_empty_folders
from unittest.mock import patch, call
import os
from smap_io.download import wget_download



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



