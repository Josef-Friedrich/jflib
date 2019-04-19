import os
import unittest
from jflib.config_reader import \
    ConfigReader, \
    Environ, \
    Ini, \
    validate_key, \
    Reader, \
    ConfigValueError

# [Classical]
# name = Mozart

# [Romantic]
# name = Schumann
INI_FILE = os.path.join(os.path.dirname(__file__), 'files', 'config.ini')

os.environ['XXX__Classical__name'] = 'Mozart'
os.environ['XXX__Baroque__name'] = 'Bach'


class TestFunctionValidateKey(unittest.TestCase):

    def test_valid(self):
        self.assertTrue(validate_key('test'))
        self.assertTrue(validate_key('test_1'))
        self.assertTrue(validate_key('1'))
        self.assertTrue(validate_key('a'))
        self.assertTrue(validate_key('ABC_abc_123'))

    def test_invalid(self):
        with self.assertRaises(ValueError) as context:
            validate_key('l o l')
        self.assertEqual(
            str(context.exception),
            'The key “l o l” contains invalid characters '
            '(allowed: a-zA-Z0-9_).',
        )
        with self.assertRaises(ValueError) as context:
            validate_key('ö')


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
        os.environ['Avantgarde__name'] = 'Stockhausen'
        environ = Environ()
        self.assertEqual(environ.get('Avantgarde', 'name'), 'Stockhausen')
        del os.environ['Avantgarde__name']

    def test_exception(self):
        environ = Environ()
        with self.assertRaises(ConfigValueError) as cm:
            environ.get('xxxAvantgarde', 'xxxname')
        self.assertEqual(
            str(cm.exception),
            'Environment variable not found: xxxAvantgarde__xxxname',
        )


class TestClassIni(unittest.TestCase):

    def test_method_get(self):
        ini = Ini(path=INI_FILE)
        self.assertEqual(ini.get('Classical', 'name'), 'Mozart')
        self.assertEqual(ini.get('Romantic', 'name'), 'Schumann')

    def test_exception(self):
        ini = Ini(path=INI_FILE)
        with self.assertRaises(ConfigValueError) as cm:
            ini.get('lol', 'lol')
        self.assertEqual(
            str(cm.exception),
            'Configuration value could not be found (section “lol” key '
            '“lol”).',
        )


class TestReader(unittest.TestCase):

    def test_ini_first(self):
        reader = Reader(Ini(INI_FILE), Environ(prefix='XXX'))
        self.assertEqual(reader.get('Classical', 'name'), 'Mozart')

    def test_environ_first(self):
        reader = Reader(Environ('XXX'), Ini(INI_FILE))
        self.assertEqual(reader.get('Baroque', 'name'), 'Bach')

    def test_exception(self):
        reader = Reader(Environ('XXX'), Ini(INI_FILE))
        with self.assertRaises(ValueError) as context:
            reader.get('lol', 'lol')
        self.assertEqual(
            str(context.exception),
            'Configuration value could not be found (section “lol” key '
            '“lol”).',
        )


class TestClassConfigReader(unittest.TestCase):

    def test_valid(self):
        config = ConfigReader(Ini(INI_FILE), Environ(prefix='XXX'))
        self.assertEqual(config.Classical.name, 'Mozart')
