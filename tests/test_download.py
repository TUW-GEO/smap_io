# test_downloader.py



import smap_io.download as download
# test_integration.py
import io
import json
import os
from datetime import datetime
from types import SimpleNamespace

import pytest

# ---------------------------
# build_version_query_params
# ---------------------------

def test_build_version_query_params():
    res = download.build_version_query_params("009")
    assert res == "&version=009&version=09&version=9"


# ---------------------------
# filter_add_wildcards
# ---------------------------

@pytest.mark.parametrize(
    "inp,expected",
    [
        ("abc", "*abc*"),
        ("*abc", "*abc*"),
        ("abc*", "*abc*"),
        ("*abc*", "*abc*")
    ],
)
def test_filter_add_wildcards(inp, expected):
    assert download.filter_add_wildcards(inp) == expected


# ---------------------------
# build_filename_filter
# ---------------------------

def test_build_filename_filter_multiple():
    res = download.build_filename_filter("A,B")
    assert "&options[producer_granule_id][pattern]=true" in res
    assert "&producer_granule_id[]=*A*" in res
    assert "&producer_granule_id[]=*B*" in res


# ---------------------------
# build_query_params_str
# ---------------------------

def test_build_query_params_str_polygon_takes_precedence():
    params = download.build_query_params_str(
        short_name="SPL3SMP",
        version="009",
        time_start="2025-10-01",
        time_end="2025-10-30",
        bounding_box="0,0,1,1",
        polygon="1,2,3,4,5,6",
        filename_filter=None,
        provider="TESTPROV",
    )

    assert "&short_name=SPL3SMP" in params
    assert "&provider=TESTPROV" in params
    assert "&polygon=1,2,3,4,5,6" in params
    assert "&bounding_box=" not in params
    assert "&temporal[]=2025-10-01,2025-10-30" in params


# ---------------------------
# get_speed
# ---------------------------

def test_get_speed_zero_time():
    assert download.get_speed(0, 1000) == ""
    assert download.get_speed(-1, 1000) == ""


def test_get_speed_positive():
    result = download.get_speed(2, 2000)  # 2000/2 = 1000 B/s
    assert result == "1.0kB/s"


# ---------------------------
# cmr_read_in_chunks
# ---------------------------

def test_cmr_read_in_chunks():
    data = b"abcdefghijklmnopqrstuvwxyz"
    stream = io.BytesIO(data)

    chunks = list(download.cmr_read_in_chunks(stream, chunk_size=5))
    assert b"".join(chunks) == data
    assert all(len(chunk) <= 5 for chunk in chunks)


# ---------------------------
# cmr_filter_urls
# ---------------------------

def test_cmr_filter_urls():
    entry_links = [
        # invalid / skipped
        {"title": "data", "rel": "data#"},                         # no href
        {"href": "x1", "inherited": True, "rel": "data#"},         # inherited
        {"href": "x2", "rel": "nope"},                             # rel not data#
        {"href": "x3", "title": "opendap", "rel": "data#"},        # opendap
        {"href": "file.dmrpp", "rel": "metadata#"},                # metadata .dmrpp
        {"href": "s3credentials", "rel": "metadata#"},             # excluded explicitly

        # valid
        {"href": "https://example.com/file1.h5", "rel": "data#"},
        {"href": "https://example.com/file1.h5", "rel": "data#"},  # duplicate filename
        {"href": "https://example.com/file2.nc", "rel": "data#"},
    ]

    search_results = {"feed": {"entry": [{"links": entry_links}]}}

    urls = download.cmr_filter_urls(search_results)

    assert "https://example.com/file1.h5" in urls
    assert "https://example.com/file2.nc" in urls
    assert "file.dmrpp" not in urls
    assert "s3credentials" not in urls
    assert urls.count("https://example.com/file1.h5") == 1


def test_cmr_filter_urls_empty():
    assert download.cmr_filter_urls({}) == []
    assert download.cmr_filter_urls({"feed": {}}) == []
    assert download.cmr_filter_urls({"feed": {"entry": [{}]}}) == []


# ---------------------------
# get_start_date
# ---------------------------

def test_get_start_date():
    d = download.get_start_date("SPL3SMP")
    assert d == datetime(2015, 3, 31, 0)


# ======================================================================


# -------------------------
# Helpers for fake responses
# -------------------------
class FakeResponse:
    def __init__(self, body_bytes=b"", headers=None):
        self._body = io.BytesIO(body_bytes)
        self.headers = headers or {}
        # .info() in original code is used then cast to dict(response.info()).items()
        # We'll make info() return a dict-like object
        self._info = dict(self.headers)

    def info(self):
        return self._info

    def read(self, amt=None):
        # mimic urllib response.read() returning bytes
        return self._body.read() if amt is None else self._body.read(amt)

    @property
    def url(self):
        return "https://example.fake/resource"


# -------------------------
# Tests for cmr_search
# -------------------------
def test_cmr_search_multiple_pages(monkeypatch):
    """
    cmr_search performs iterative paging using the 'cmr-search-after' header
    and aggregates URLs returned by cmr_filter_urls.
    We'll monkeypatch:
      - download.get_provider_for_collection -> returns a provider string
      - download.urlopen (the function imported in the downloadule) -> returns two FakeResponses:
         1) first response: has 'cmr-hits' header > CMR_PAGE_SIZE to force the '...' printing branch,
            includes a cmr-search-after header to request next page, and returns a JSON body
            with at least one entry link.
         2) second response: returns JSON without useful links so loop exits.
    """
    # Provide a provider
    monkeypatch.setattr(download, "get_provider_for_collection", lambda sn, v: "TESTPROV")

    # Build a first "page" JSON with one entry that contains a valid data link
    first_feed = {
        "feed": {
            "entry": [
                {
                    "links": [
                        {"href": "https://example.com/file1.h5", "rel": "data#"},
                        # one invalid link for coverage
                        {"href": "https://example.com/skip.dmrpp", "rel": "metadata#"}
                    ]
                }
            ]
        }
    }
    second_feed = {"feed": {"entry": []}}

    # Responses: first has cmr-hits and cmr-search-after header, second has none
    first_body = json.dumps(first_feed).encode("utf-8")
    second_body = json.dumps(second_feed).encode("utf-8")

    responses = [
        FakeResponse(body_bytes=first_body, headers={"cmr-hits": "2", "cmr-search-after": "page2"}),
        FakeResponse(body_bytes=second_body, headers={}),
    ]

    # monkeypatch download.urlopen to pop responses in order
    def fake_urlopen(req, context=None):
        return responses.pop(0)

    monkeypatch.setattr(download, "urlopen", fake_urlopen)

    # Run search (quiet True to reduce prints)
    urls = download.cmr_search(short_name="SPL3SMP", version="009",
                          time_start="2025-10-01", time_end="2025-10-10",
                          quiet=True)

    # We expect the valid data link to be present
    assert "https://example.com/file1.h5" in urls
    # dmrpp link should be filtered out by cmr_filter_urls
    assert not any(u.endswith(".dmrpp") for u in urls)


# -------------------------
# Tests for cmr_download
# -------------------------
def test_cmr_download_writes_file(tmp_path, monkeypatch):
    """
    Test that cmr_download writes a file under download_dir/YYYY.MM/filename
    We'll:
      - set download.download_dir to tmp_path
      - provide a URL whose filename contains a date token in the 5th underscore field
      - monkeypatch download.get_login_response to return a FakeResponse with content
    """
    # Prepare a fake URL with filename containing date in 5th underscore chunk
    # Example filename format used in code: parts split by '_' and index 4 is date 'YYYYMMDD'
    filename = "A_B_C_D_20250701_E.h5"
    url = "https://example.com/" + filename

    # Make download_dir a temp directory
    monkeypatch.setattr(download, "download_dir", str(tmp_path))

    # Create response bytes and headers
    file_content = b"hello world content"
    length = len(file_content)
    fake_response = FakeResponse(body_bytes=file_content, headers={"content-length": str(length)})

    # Response object must support iteration via cmr_read_in_chunks (it calls read(chunk_size))
    # FakeResponse implemented read, so cmr_read_in_chunks will work.

    # Patch get_login_response to return our fake response
    monkeypatch.setattr(download, "get_login_response", lambda url, credentials, token: fake_response)

    # Ensure target dir does not exist initially
    # Call download with quiet True to suppress progress printing
    download.cmr_download([url], username="user", password="pass", force=False, quiet=True)

    # Determine expected file path created by cmr_download:
    # date_str = filename.split('_')[4] -> '20250701'
    file_date = "2025.07.01"
    expected_dir = tmp_path / file_date
    expected_path = expected_dir / filename

    assert expected_path.exists()
    # File content should match
    with expected_path.open("rb") as fh:
        data = fh.read()
    assert data == file_content


def test_cmr_download_skips_existing_same_size(tmp_path, monkeypatch, capsys):
    """
    If a file already exists with the same size and force==False, cmr_download should skip writing it.
    We'll create an existing file with the same byte length and ensure the function does not overwrite.
    """
    filename = "A_B_C_D_20250702_E.h5"
    url = "https://example.com/" + filename
    monkeypatch.setattr(download, "download_dir", str(tmp_path))

    content = b"existing content"
    length = len(content)
    fake_response = FakeResponse(body_bytes=b"NEW_CONTENT_SHOULD_NOT_BE_WRITTEN", headers={"content-length": str(length)})

    monkeypatch.setattr(download, "get_login_response", lambda url, credentials, token: fake_response)

    # Create the directory and existing file with the same size
    file_date = "2025.07.02"
    target_dir = tmp_path / file_date
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    with target_path.open("wb") as fh:
        fh.write(content)
    assert target_path.stat().st_size == length

    # Now call cmr_download; since sizes match and force is False, it should skip (no exception)
    download.cmr_download([url], username="u", password="p", force=False, quiet=True)

    # After call, the file should still contain the original content
    with target_path.open("rb") as fh:
        newdata = fh.read()
    assert newdata == content


# -------------------------
# Tests for parse_args
# -------------------------
def test_parse_args_supplied_times(monkeypatch, capsys):
    """
    parse_args should accept provided time_start and time_end and set defaults correctly.
    We'll call parse_args with explicit time_start and time_end and check resulting attributes.
    """
    argv = ["--short_name", "SPL3SMP", "--version", "009",
            "--time_start", "2025-10-01", "--time_end", "2025-10-05",
            "--output", str(os.getcwd()),
            "--username", "u", "--password", "p"]
    args = download.parse_args(argv)

    assert args.short_name == "SPL3SMP"
    assert args.version == "009"
    assert args.time_start == "2025-10-01"
    assert args.time_end == "2025-10-05"
    assert args.output == os.getcwd()
    assert args.username == "u"
    assert args.password == "p"

    # Ensure parse_args printed the status line (it prints a message)
    captured = capsys.readouterr()
    assert "Downloading SMAP" in captured.out


def test_parse_args_defaults_time(monkeypatch):
    """
    When time_start or time_end are omitted, parse_args uses get_start_date and datetime.now().
    We'll monkeypatch get_start_date and datetime.now to known values for deterministic output.
    """
    # patch get_start_date to return a fixed datetime
    monkeypatch.setattr(download, "get_start_date", lambda sn: datetime(2015, 3, 31))
    # patch datetime.now used inside parse_args: we need to patch the datetime class in the module
    class DummyDT:
        @classmethod
        def now(cls):
            return datetime(2020, 1, 2)

    monkeypatch.setattr(download, "datetime", DummyDT)

    argv = ["--short_name", "SPL3SMP", "--version", "009", "--output", str(os.getcwd())]
    args = download.parse_args(argv)

    # get_start_date returns a datetime and parse_args sets args.time_start to its "%Y-%m-%d"
    assert args.time_start == "2015-03-31"
    # args.time_end should be DummyDT.now().strftime("%Y-%m-%d")
    assert args.time_end == "2020-01-02"


