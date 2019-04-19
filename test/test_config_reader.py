import os
import unittest
from jflib.config_reader import ConfigReader, Environ, Ini, ConfigValueError


class TestClassEnviron(unittest.TestCase):

    def test_method_get(self):
        os.environ['AAA__bridge__ip'] = '1.2.3.4'
        os.environ['AAA__bridge__username'] = 'test'
        environ = Environ(prefix='AAA')
        self.assertEqual(environ.get('bridge', 'ip'), '1.2.3.4')
        self.assertEqual(environ.get('bridge', 'username'), 'test')

    def test_exception(self):
        environ = Environ(prefix='AAA')
        with self.assertRaises(ConfigValueError) as cm:
            environ.get('lol', 'lol')
        self.assertEqual(
            str(cm.exception),
            'Environment variable not found: AAA__lol__lol',
        )


class TestClassEnvironWithoutPrefix(unittest.TestCase):

    def test_method_get(self):
        os.environ['xxxbridge__ip'] = '1.2.3.4'
        os.environ['xxxbridge__username'] = 'test'
        environ = Environ()
        self.assertEqual(environ.get('xxxbridge', 'ip'), '1.2.3.4')
        self.assertEqual(environ.get('xxxbridge', 'username'), 'test')

    def test_exception(self):
        environ = Environ()
        with self.assertRaises(ConfigValueError) as cm:
            environ.get('xxxlol', 'lol')
        self.assertEqual(
            str(cm.exception),
            'Environment variable not found: xxxlol__lol',
        )


class TestClassIni(unittest.TestCase):

    def setUp(self):
        self.ini_file = os.path.join(os.path.dirname(__file__), 'files',
                                     'config.ini')

    def test_method_get(self):
        ini = Ini(path=self.ini_file)
        self.assertEqual(ini.get('Classical', 'name'), 'Mozart')
        self.assertEqual(ini.get('Romantic', 'profession'), 'composer')

    def test_exception(self):
        ini = Ini(path=self.ini_file)
        with self.assertRaises(ConfigValueError) as cm:
            ini.get('lol', 'lol')
        self.assertEqual(
            str(cm.exception),
            'Configuration value could not be found (section “lol” key '
            '“lol”).',
        )


class TestClassConfiguration(unittest.TestCase):

    def test_environ(self):
        os.environ['AAA__bridge__ip'] = '1.2.3.4'
        os.environ['AAA__bridge__username'] = 'test'
        config = ConfigReader(environ_prefix='AAA')
        self.assertEqual(config.get('bridge', 'ip'), '1.2.3.4')
        self.assertEqual(config.get('bridge', 'username'), 'test')

    def test_exception(self):
        config = ConfigReader(environ_prefix='AAA')
        with self.assertRaises(ValueError) as cm:
            config.get('lol', 'lol')
        self.assertEqual(
            str(cm.exception),
            'Configuration value could not be found (section “lol” key '
            '“lol”).',
        )
