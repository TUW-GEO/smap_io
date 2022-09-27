"""
Download SMAP.
"""
import os
import sys
import glob
import argparse
from functools import partial

import trollsift.parser as parser
from datetime import datetime
from datedown.interface import mkdate
from datedown.dates import daily
from datedown.urlcreator import create_dt_url
from datedown.fname_creator import create_dt_fpath
from datedown.interface import download_by_dt
import subprocess
import tempfile
from multiprocessing import Pool


def dates_empty_folders(img_dir, crid=None):
    """
    Checks the download directory for date with empty folders.

    Parameters
    ----------
    img_dir : str
        Directory to count files and folders in
    crid : int, optional (default:None)
        If crid is passed, check if any file in each dir contains the crid in
        the name, else check if there is any file at all.
    Returns
    -------
    miss_dates : list
        Dates where a folder exists but no file is inside
    """

    missing = []
    for dir, subdirs, files in os.walk(img_dir):
        if len(subdirs) != 0:
            continue
        if crid:
            cont = [str(crid) in afile for afile in files]
            if not any(cont):
                missing.append(dir)
        else:
            cont = True if len(files) > 0 else False
            if not cont:
                missing.append(dir)

    miss_dates = [
        datetime.strptime(
            os.path.basename(os.path.normpath(miss_path)), '%Y.%m.%d')
        for miss_path in missing
    ]

    return sorted(miss_dates)


def wget_download(url,
                  target,
                  username=None,
                  password=None,
                  cookie_file=None,
                  recursive=False,
                  filetypes=None,
                  robots_off=False):
    """
    copied from datedown and modified.

    Download a url using wget.
    Retry as often as necessary and store cookies if
    authentification is necessary.

    Parameters
    ----------
    url: string
        URL to download
    target: string
        path on local filesystem where to store the downloaded file
    username: string, optional
        username
    password: string, optional
        password
    cookie_file: string, optional
        file where to store cookies
    recursive: boolean, optional
        If set then no exact filenames can be given.
        The data will then be downloaded recursively and stored in the target folder.
    filetypes: list, optional
        list of file extension to download, any others will no be downloaded
    robots_off : bool
        Don't apply server robots rules.
    """
    cmd_list = ['wget', url, '--retry-connrefused', '--no-check-certificate']

    cmd_list = cmd_list + ['--auth-no-challenge', 'on']

    if recursive:
        cmd_list = cmd_list + ['-P', target]
        cmd_list = cmd_list + ['-nd']
        cmd_list = cmd_list + ['-np']
        cmd_list = cmd_list + ['-r']
    else:
        cmd_list = cmd_list + ['-O', target]

    if robots_off:
        cmd_list = cmd_list + ['-e', 'robots=off']

    if filetypes is not None:
        cmd_list = cmd_list + ['-A ' + ','.join(filetypes)]

    target_path = os.path.split(target)[0]
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    if username is not None:
        cmd_list.append('--user={}'.format(username))
    if password is not None:
        cmd_list.append('--password={}'.format(password))
    if cookie_file is not None:
        cmd_list = cmd_list + [
            '--load-cookies', cookie_file, '--save-cookies', cookie_file,
            '--keep-session-cookies'
        ]

    subprocess.call(" ".join(cmd_list), shell=True)


def check_dl(url_target):
    '''
    Check if the folder exists and is not empty (False if not)
    '''
    return os.path.isdir(url_target) and not len(os.listdir(url_target)) == 0


def wget_map_download(url_target,
                      username=None,
                      password=None,
                      cookie_file=None,
                      recursive=False,
                      filetypes=None,
                      robots_off=False):
    """
    copied from datedown and modified.

    variant of the function that only takes one argument.
    Otherwise map_async of the multiprocessing module can not work with the function.

    Parameters
    ----------
    url_target: list
        first element the url, second the target string
    username: string, optional
        username
    password: string, optional
        password
    cookie_file: string, optional
        file where to store cookies
    recursive: boolean, optional
        If set then no exact filenames can be given.
        The data will then be downloaded recursively and stored in the target folder.
    filetypes: list, optional
        list of file extension to download, any others will no be downloaded
    robots_off : bool
        Don't apply server robots rules.
    """

    # repeats the download once in cases where no files are downloaded.
    i = 0
    while (not check_dl(url_target[1])) and i < 5:
        wget_download(
            url_target[0],
            url_target[1],
            username=username,
            password=password,
            cookie_file=cookie_file,
            recursive=recursive,
            filetypes=filetypes,
            robots_off=robots_off)
        i += 1


def download(urls,
             targets,
             num_proc=1,
             username=None,
             password=None,
             recursive=False,
             filetypes=None,
             robots_off=False):
    """
    copied from datedown.

    Download the urls and store them at the target filenames.

    Parameters
    ----------
    urls: iterable
        iterable over url strings
    targets: iterable
        paths where to store the files
    num_proc: int, optional
        Number of parallel downloads to start
    username: string, optional
        Username to use for login
    password: string, optional
        Password to use for login
    recursive: boolean, optional
        If set then no exact filenames can be given.
        The data will then be downloaded recursively and stored in the target folder.
    filetypes: list, optional
        list of file extension to download, any others will no be downloaded
    robots_off : bool
        Don't apply server robots rules.
    """

    def update(r):
        return

    def error(e):
        return

    cf = tempfile.NamedTemporaryFile()
    cookie_file = cf.name
    cf.close()

    args = []
    for u, t in zip(urls, targets):
        args.append([[u, t], username, password, cookie_file, recursive,
                     filetypes, robots_off])

    if num_proc == 1:
        for arg in args:
            try:
                r = wget_map_download(*arg)
                update(r)
            except Exception as e:
                error(e)
    else:
        with Pool(num_proc) as pool:
            for arg in args:
                pool.apply_async(
                    wget_map_download,
                    arg,
                    callback=update,
                    error_callback=error,
                )
            pool.close()
            pool.join()


def folder_get_first_last(
        root,
        fmt="SMAP_L3_SM_P_{time:%Y%m%d}_R{orbit:05d}_{proc_number:03d}.h5",
        subpaths=['{:%Y.%m.%d}']):
    """
    Get first and last product which exists under the root folder.

    Parameters
    ----------
    root: string
        Root folder on local filesystem
    fmt: string, optional
        formatting string
    subpaths: list, optional
        format of the subdirectories under root.

    Returns
    -------
    start: datetime.datetime
        First found product datetime
    end: datetime.datetime
        Last found product datetime
    """
    start = None
    end = None
    first_folder = get_first_folder(root, subpaths)
    last_folder = get_last_folder(root, subpaths)

    if first_folder is not None:
        files = sorted(
            glob.glob(os.path.join(first_folder, parser.globify(fmt))))
        data = parser.parse(fmt, os.path.split(files[0])[1])
        start = data['time']

    if last_folder is not None:
        files = sorted(
            glob.glob(os.path.join(last_folder, parser.globify(fmt))))
        data = parser.parse(fmt, os.path.split(files[-1])[1])
        end = data['time']

    return start, end


def get_last_folder(root, subpaths):
    directory = root
    for level, subpath in enumerate(subpaths):
        last_dir = get_last_formatted_dir_in_dir(directory, subpath)
        if last_dir is None:
            directory = None
            break
        directory = os.path.join(directory, last_dir)
    return directory


def get_first_folder(root, subpaths):
    directory = root
    for level, subpath in enumerate(subpaths):
        last_dir = get_first_formatted_dir_in_dir(directory, subpath)
        if last_dir is None:
            directory = None
            break
        directory = os.path.join(directory, last_dir)
    return directory


def get_last_formatted_dir_in_dir(folder, fmt):
    """
    Get the (alphabetically) last directory in a directory
    which can be formatted according to fmt.
    """
    last_elem = None
    root_elements = sorted(os.listdir(folder))
    for root_element in root_elements[::-1]:
        if os.path.isdir(os.path.join(folder, root_element)):
            if parser.validate(fmt, root_element):
                last_elem = root_element
                break
    return last_elem


def get_first_formatted_dir_in_dir(folder, fmt):
    """
    Get the (alphabetically) first directory in a directory
    which can be formatted according to fmt.
    """
    first_elem = None
    root_elements = sorted(os.listdir(folder))
    for root_element in root_elements:
        if os.path.isdir(os.path.join(folder, root_element)):
            if parser.validate(fmt, root_element):
                first_elem = root_element
                break
    return first_elem


def get_start_date(product):
    if product.startswith("SPL3SMP"):
        return datetime(2015, 3, 31, 0)


def parse_args(args):
    """
    Parse command line parameters for recursive download

    :param args: command line parameters as list of strings
    :return: command line parameters as :obj:`argparse.Namespace`
    """
    parser = argparse.ArgumentParser(
        description="Download SMAP data. Register at https://urs.earthdata.nasa.gov/ first."
    )
    parser.add_argument(
        "localroot", help='Root of local filesystem where the data is stored.')
    parser.add_argument(
        "-s",
        "--start",
        type=mkdate,
        help=(
            "Startdate. Either in format YYYY-MM-DD or YYYY-MM-DDTHH:MM."
            " If not given then the target folder is scanned for a start date."
            " If no data is found there then the first available date of the product is used."
        ))
    parser.add_argument(
        "-e",
        "--end",
        type=mkdate,
        help=("Enddate. Either in format YYYY-MM-DD or YYYY-MM-DDTHH:MM."
              " If not given then the current date is used."))
    parser.add_argument(
        "--product",
        type=str,
        default="SPL3SMP.008",
        help='SMAP product to download. (default: SPL3SMP.008).'
        ' See also https://n5eil01u.ecs.nsidc.org/SMAP/ ')
    parser.add_argument(
        "--filetypes",
        nargs="*",
        default=["h5", "nc"],
        help="File types (extensions) to download. Files with"
        "other extensions are ignored. "
        "Default is equivalent to --filetypes h5 nc")
    parser.add_argument("--username", help='Username to use for download.')
    parser.add_argument("--password", help='password to use for download.')
    parser.add_argument(
        "--n_proc",
        default=1,
        type=int,
        help='Number of parallel processes to use for downloading.')
    args = parser.parse_args(args)
    # set defaults that can not be handled by argparse

    if args.start is None or args.end is None:
        first, last = folder_get_first_last(args.localroot)
        if args.start is None:
            if last is None:
                args.start = get_start_date(args.product)
            else:
                args.start = last
        if args.end is None:
            args.end = datetime.now()

    args.urlroot = 'https://n5eil01u.ecs.nsidc.org'
    args.urlsubdirs = ['SMAP', args.product, '%Y.%m.%d']
    args.localsubdirs = ['%Y.%m.%d']

    print(
        f"Downloading SMAP {args.product} data from {args.start.isoformat()} "
        f"to {args.end.isoformat()} into folder {args.localroot}.")

    return args


def main(args):
    args = parse_args(args)

    dts = list(daily(args.start, args.end))
    i = 0
    while (len(dts) != 0) and i < 3:  # after 3 reties abort
        url_create_fn = partial(
            create_dt_url,
            root=args.urlroot,
            fname='',
            subdirs=args.urlsubdirs)
        fname_create_fn = partial(
            create_dt_fpath,
            root=args.localroot,
            fname='',
            subdirs=args.localsubdirs)
        down_func = partial(
            download,
            num_proc=args.n_proc,
            username=args.username,
            password=args.password,
            recursive=True,
            filetypes=args.filetypes,
            robots_off=True)

        download_by_dt(
            dts, url_create_fn, fname_create_fn, down_func, recursive=True)

        dts = dates_empty_folders(args.localroot)  # missing dates
        i += 1

    if len(dts) != 0:
        print('----------------------------------------------------------')
        print('----------------------------------------------------------')
        print('No data has been downloaded for the following dates:')
        for date in dts:
            print(str(date.date()))


def run():
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
