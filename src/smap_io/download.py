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
# ----------------------------------------------------------------------------
from __future__ import print_function
import argparse
import base64
import itertools
import json
import math
import netrc
import os
import os.path
import ssl
import sys
import time
from datetime import datetime
from getpass import getpass
import trollsift.parser as parser
import glob


try:
    from urllib.parse import urlparse
    from urllib.request import urlopen, Request, build_opener, \
        HTTPCookieProcessor
    from urllib.error import HTTPError, URLError
except ImportError:
    from urlparse import urlparse
    from urllib2 import urlopen, Request, build_opener, HTTPCookieProcessor, \
        HTTPError, URLError

# ------------------ Default Parameters ------------------
short_name = "SPL3SMP"
version = "009"
time_start = "2025-10-01"
time_end = "2025-10-30"
bounding_box = ""
polygon = ""
filename_filter = ""
url_list = []

# Default download folder (can be overridden with --output)
download_dir = os.getcwd()

CMR_URL = "https://cmr.earthdata.nasa.gov"
URS_URL = "https://urs.earthdata.nasa.gov"
CMR_PAGE_SIZE = 2000
CMR_FILE_URL = (
    "{0}/search/granules.json?"
    "&sort_key[]=start_date&sort_key[]=producer_granule_id"
    "&page_size={1}".format(CMR_URL, CMR_PAGE_SIZE)
)
CMR_COLLECTIONS_URL = "{0}/search/collections.json?".format(CMR_URL)
FILE_DOWNLOAD_MAX_RETRIES = 3


# ------------------ Login Functions ------------------
def get_username():
    try:
        do_input = raw_input  # Python 2 compatibility
    except NameError:
        do_input = input
    return do_input(
        "Earthdata username (or press Return to use a bearer token): ")


def get_password():
    password = ""
    while not password:
        password = getpass("password: ")
    return password





# ------------------ Query Building ------------------
def build_version_query_params(version):
    desired_pad_length = 3
    if len(version) > desired_pad_length:
        print('Version string too long: "{0}"'.format(version))
        quit()
    version = str(int(version))  # Strip leading zeros
    query_params = ""
    while len(version) <= desired_pad_length:
        padded_version = version.zfill(desired_pad_length)
        query_params += "&version={0}".format(padded_version)
        desired_pad_length -= 1
    return query_params


def filter_add_wildcards(f):
    if not f.startswith("*"):
        f = "*" + f
    if not f.endswith("*"):
        f = f + "*"
    return f


def build_filename_filter(filename_filter):
    filters = filename_filter.split(",")
    result = "&options[producer_granule_id][pattern]=true"
    for f in filters:
        result += "&producer_granule_id[]=" + filter_add_wildcards(f)
    return result


def build_query_params_str(short_name, version, time_start="", time_end="",
                           bounding_box=None, polygon=None,
                           filename_filter=None, provider=None):
    params = "&short_name={0}".format(short_name)
    params += build_version_query_params(version)
    if time_start or time_end:
        params += "&temporal[]={0},{1}".format(time_start, time_end)
    if polygon:
        params += "&polygon={0}".format(polygon)
    elif bounding_box:
        params += "&bounding_box={0}".format(bounding_box)
    if filename_filter:
        params += build_filename_filter(filename_filter)
    if provider:
        params += "&provider={0}".format(provider)
    return params


def build_cmr_query_url(short_name, version, time_start, time_end,
                        bounding_box=None, polygon=None, filename_filter=None,
                        provider=None):
    params = build_query_params_str(short_name, version, time_start, time_end,
                                    bounding_box, polygon, filename_filter,
                                    provider)
    return CMR_FILE_URL + params


# ------------------ Download Utilities ------------------
def get_speed(time_elapsed, chunk_size):
    if time_elapsed <= 0:
        return ""
    speed = chunk_size / time_elapsed
    if speed <= 0:
        speed = 1
    size_name = ("", "k", "M", "G", "T", "P", "E", "Z", "Y")
    i = int(math.floor(math.log(speed, 1000)))
    p = math.pow(1000, i)
    return "{0:.1f}{1}B/s".format(speed / p, size_name[i])


def output_progress(count, total, status="", bar_len=60):
    if total <= 0:
        return
    fraction = min(max(count / float(total), 0), 1)
    filled_len = int(round(bar_len * fraction))
    percents = int(round(100.0 * fraction))
    bar = "=" * filled_len + " " * (bar_len - filled_len)
    fmt = "  [{0}] {1:3d}%  {2}   ".format(bar, percents, status)
    print("\b" * (len(fmt) + 4), end="")
    sys.stdout.write(fmt)
    sys.stdout.flush()


def cmr_read_in_chunks(file_object, chunk_size=1024 * 1024):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def get_login_response(url, credentials, token):
    opener = build_opener(HTTPCookieProcessor())
    req = Request(url)
    if token:
        req.add_header("Authorization", "Bearer {0}".format(token))
    elif credentials:
        try:
            response = opener.open(req)
            url = response.url
        except HTTPError:
            pass
        req = Request(url)
        req.add_header("Authorization", "Basic {0}".format(credentials))
    try:
        response = opener.open(req)
    except HTTPError as e:
        err = "HTTP error {0}, {1}".format(e.code, e.reason)
        if "Unauthorized" in e.reason:
            if token:
                err += ": Check your bearer token"
            else:
                err += ": Check your username and password"
            print(err)
            sys.exit(1)
        raise
    except Exception as e:
        print("Error{0}: {1}".format(type(e), str(e)))
        sys.exit(1)
    return response





def cmr_download(urls, username, password, force=False, quiet=False):
    if not urls:
        return
    url_count = len(urls)
    if not quiet:
        print("Downloading {0} files...".format(url_count))
    credentials = None
    token = None

    for index, url in enumerate(urls, start=1):
        if not credentials and not token:
            p = urlparse(url)
            if p.scheme == "https":
                # credentials, token = get_login_credentials()
                credentials = "{0}:{1}".format(username, password)
                credentials = base64.b64encode(
                    credentials.encode("ascii")).decode("ascii")

        filename = url.split("/")[-1]

        date_str = filename.split('_')[4]  # '20250701'
        file_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        download_dir_sub_path = os.path.join(download_dir,
                                             file_date.replace("-", "."))
        print(filename)
        if not os.path.exists(download_dir_sub_path):
            os.makedirs(download_dir_sub_path)
            filepath = os.path.join(download_dir, download_dir_sub_path,
                                    filename)
        else:
            filepath = os.path.join(download_dir, download_dir_sub_path,
                                    filename)

        print(filepath)
        if not quiet:
            print("{0}/{1}: {2}".format(str(index).zfill(len(str(url_count))),
                                        url_count, filename))

        for attempt in range(1, FILE_DOWNLOAD_MAX_RETRIES + 1):
            if not quiet and attempt > 1:
                print("Retrying download of {0}".format(url))
            try:
                response = get_login_response(url, credentials, token)
                length = int(response.headers["content-length"])
                try:
                    if not force and length == os.path.getsize(filepath):
                        if not quiet:
                            print("  File exists, skipping")
                        break
                except OSError:
                    pass
                count = 0
                chunk_size = min(max(length, 1), 1024 * 1024)
                max_chunks = int(math.ceil(length / chunk_size))
                time_initial = time.time()
                with open(filepath, "wb") as out_file:
                    for data in cmr_read_in_chunks(response,
                                                   chunk_size=chunk_size):
                        out_file.write(data)
                        if not quiet:
                            count += 1
                            elapsed = time.time() - time_initial
                            speed = get_speed(elapsed, count * chunk_size)
                            output_progress(count, max_chunks, status=speed)
                if not quiet:
                    print()
                break
            except (HTTPError, URLError, IOError) as e:
                print(
                    "Error downloading file {0}: {1}".format(filename, str(e)))
                if attempt == FILE_DOWNLOAD_MAX_RETRIES:
                    print(
                        "Failed to download file {0} after {1} "
                        "attempts.".format(
                            filename, FILE_DOWNLOAD_MAX_RETRIES))
                    sys.exit(1)

                # ------------------ CMR URL Filtering ------------------


def cmr_filter_urls(search_results):
    if "feed" not in search_results or "entry" not in \
            search_results["feed"]:
        return []
    entries = [e["links"] for e in search_results["feed"]["entry"]
               if "links" in e]
    links = list(itertools.chain(*entries))
    urls = []
    unique_filenames = set()
    for link in links:
        if "href" not in link or (
                "inherited" in link and link["inherited"]):
            continue
        if "rel" in link and "data#" not in link["rel"]:
            continue
        if "title" in link and "opendap" in link["title"].lower():
            continue
        filename = link["href"].split("/")[-1]
        if ("metadata#" in link.get("rel", "") and (
                filename.endswith(
                    ".dmrpp") or filename == "s3credentials")):
            continue
        if filename in unique_filenames:
            continue
        unique_filenames.add(filename)
        urls.append(link["href"])
    return urls

    # ------------------ Provider Selection ------------------


def check_provider_for_collection(short_name, version, provider):
    query_params = build_query_params_str(short_name=short_name,
                                          version=version,
                                          provider=provider)
    cmr_query_url = CMR_COLLECTIONS_URL + query_params
    try:
        response = urlopen(Request(cmr_query_url))
    except Exception as e:
        print("Error: " + str(e))
        sys.exit(1)
    search_page = json.loads(response.read().decode("utf-8"))
    return bool(search_page.get("feed", {}).get("entry"))


def get_provider_for_collection(short_name, version):
    cloud_provider = "NSIDC_CPRD"
    if check_provider_for_collection(short_name, version,
                                     cloud_provider):
        return cloud_provider
    ecs_provider = "NSIDC_ECS"
    if check_provider_for_collection(short_name, version,
                                     ecs_provider):
        return ecs_provider
    raise RuntimeError(
        "No collection found for short_name {} and version {}".format(
            short_name, version))

    # ------------------ CMR Search ------------------


def cmr_search(short_name, version, time_start, time_end,
               bounding_box="", polygon="", filename_filter="",
               quiet=False):
    provider = get_provider_for_collection(short_name, version)
    cmr_query_url = build_cmr_query_url(provider=provider,
                                        short_name=short_name,
                                        version=version,
                                        time_start=time_start,
                                        time_end=time_end,
                                        bounding_box=bounding_box,
                                        polygon=polygon,
                                        filename_filter=filename_filter)
    if not quiet:
        print("Querying for data:\n\t{0}\n".format(cmr_query_url))

    cmr_paging_header = "cmr-search-after"
    cmr_page_id = None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    urls = []
    hits = 0
    while True:
        req = Request(cmr_query_url)
        if cmr_page_id:
            req.add_header(cmr_paging_header, cmr_page_id)
        try:
            response = urlopen(req, context=ctx)
        except Exception as e:
            print("Error: " + str(e))
            sys.exit(1)

        headers = {k.lower(): v for k, v in
                   dict(response.info()).items()}
        if not cmr_page_id:
            hits = int(headers.get("cmr-hits", 0))
            if not quiet:
                print("Found {0} matches.".format(
                    hits) if hits > 0 else "Found no matches.")

        cmr_page_id = headers.get(cmr_paging_header)
        search_page = json.loads(response.read().decode("utf-8"))
        url_scroll_results = cmr_filter_urls(search_page)
        if not url_scroll_results:
            break
        if not quiet and hits > CMR_PAGE_SIZE:
            print(".", end="")
            sys.stdout.flush()
        urls += url_scroll_results
    if not quiet and hits > CMR_PAGE_SIZE:
        print()
    return urls

def get_start_date(short_name):
    if short_name.startswith("SPL3SMP"):
        return datetime(2015, 3, 31, 0)


def parse_args(args):
    # Use argparse instead of getopt for argument parsing
    parser = argparse.ArgumentParser(
        description="NSIDC Data Download Script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--filetypes",
        nargs="*",
        default=["h5"],
        help="File types (extensions) to download. Files with"
             "other extensions are ignored. "
             "Default is equivalent to --filetypes h5 nc")
    # Add arguments
    parser.add_argument(
        "--short_name", type=str, default="SPL3SMP",
        help="Short name of the dataset to download (e.g., SPL3SMP)."
    )
    parser.add_argument(
        "--version", type=str, default="009",
        help="Version of the dataset (e.g., 009)."
    )
    parser.add_argument(
        "--time_start", type=str, required=False,
        help="Start time for the dataset query (e.g., 2025-10-01)."
    )
    parser.add_argument(
        "--time_end", type=str, required=False,
        help="End time for the dataset query (e.g., 2025-10-30)."
    )
    parser.add_argument(
        "--username", type=str,
        help="Earthdata username for authentication."
    )
    parser.add_argument(
        "--password", type=str,
        help="Earthdata password for authentication."
    )
    parser.add_argument(
        "--output", "-o", type=str, default=os.getcwd(),
        help="Folder where downloaded files will be saved."
    )
    parser.add_argument(
        "--force", "-f", action="store_true", default=False,
        help="Force re-download of files even if they already exist."
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", default=False,
        help="Suppress verbose output."
    )

    # Parse the arguments
    args = parser.parse_args(args)
    d = 1
    if args.time_start is None:
        args.time_start = get_start_date(args.short_name).strftime("%Y-%m-%d")

    if args.time_end is None:
        args.time_end = datetime.now().strftime("%Y-%m-%d")

    print(
        f"Downloading SMAP {args.short_name} + {args.version} data f"
        f"rom {args.time_start.format()} "
        f"to {args.time_end.format()} into folder {args.output}.")

    return args


def main(argv):
    global bounding_box, polygon, filename_filter, url_list, download_dir

    args = parse_args(argv)
    # Assign parsed arguments to variables
    short_name = args.short_name
    version = args.version
    time_start = args.time_start
    time_end = args.time_end
    download_dir = args.output
    force = args.force
    quiet = args.quiet

    # Make sure the output directory exists
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Prompt for username/password if not provided
    username = args.username or get_username()
    password = args.password or get_password()

    try:
        # Call search and download functions
        if not url_list:
            url_list = cmr_search(
                short_name, version, time_start, time_end,
                bounding_box=bounding_box, polygon=polygon,
                filename_filter=filename_filter, quiet=quiet
            )
        url_list = [u for u in url_list if
                    any(u.endswith(f".{ext}") for ext in args.filetypes)]
        cmr_download(url_list, username=username, password=password,
                     force=force, quiet=quiet)
    except KeyboardInterrupt:
        print("\nDownload interrupted.")
        sys.exit(1)


def run():
    main(sys.argv[1:])


if __name__ == "__main__":
    run()