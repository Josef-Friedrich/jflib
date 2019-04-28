"""Small utility functions."""

import os
import shutil
import stat
import urllib.request


def download(url: str, dest: str):
    """Download a file and save it under a destination path.

    :param url: The URL of the file to download.
    :param dest: The path of the destination file.
    """
    with urllib.request.urlopen(url) as response, \
            open(dest, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)


def make_executable(path: str):
    """Make a file executable.

    :param path: The path of the file
    """
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)
