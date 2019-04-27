"""Small utilitly functions."""

import os
import shutil
import stat
import urllib.request


def download(url, dest):
    with urllib.request.urlopen(url) as response, \
         open(dest, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)


def make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)
