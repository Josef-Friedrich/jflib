import unittest
from jflib.utils import download, make_executable
import tempfile
import os
import stat


class TestUtils(unittest.TestCase):

    def test_download(self):
        url = 'https://raw.githubusercontent.com/' \
              'Josef-Friedrich/jflib/master/README.md'
        dest = tempfile.mkstemp()[1]
        download(url, dest)

        self.assertTrue(os.path.exists(dest))

        with open(dest, 'r') as dest_file:
            content = dest_file.read()

        self.assertIn('# jflib', content)

    def test_make_executable(self):
        tmp = tempfile.mkstemp()
        tmp_file = tmp[1]
        with open(tmp_file, 'w') as tmp_fd:
            tmp_fd.write('test')

        self.assertFalse(stat.S_IXUSR & os.stat(tmp_file)[stat.ST_MODE])

        make_executable(tmp_file)
        self.assertTrue(stat.S_IXUSR & os.stat(tmp_file)[stat.ST_MODE])
