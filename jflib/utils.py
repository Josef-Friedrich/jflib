"""Small utility functions."""

import os
import shutil
import stat
import urllib.request


def download(url, dest):
    """Download a file and save it under a destination path.

    :param str url: The URL of the file to download.
    :param str dest: The path of the destination file.
    """
    with urllib.request.urlopen(url) as response, \
            open(dest, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)


def make_executable(path):
    """Make a file executable.

    :param str path: The path of the file
    """
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)
