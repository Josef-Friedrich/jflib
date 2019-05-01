import os
import unittest
import argparse
import tempfile

from jflib.config_reader import \
    Argparse, \
    ConfigReader, \
    ConfigValueError, \
    Dictionary, \
    Environ, \
    Ini, \
    load_readers_by_keyword, \
    Reader, \
    validate_key

FILES_DIR = os.path.join(os.path.dirname(__file__), 'files')

# [Classical]
# name = Mozart

# [Romantic]
# name = Schumann
INI_FILE = os.path.join(FILES_DIR, 'config.ini')

os.environ['XXX__Classical__name'] = 'Mozart'
os.environ['XXX__Baroque__name'] = 'Bach'

parser = argparse.ArgumentParser()
parser.add_argument('--classical-name')
parser.add_argument('--baroque-name')
args = parser.parse_args(['--baroque-name', 'Bach', '--classical-name',
                          'Mozart'])


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


# Reader classes ##############################################################


class TestClassArgparse(unittest.TestCase):

    def test_method_get_without_mapping(self):
        argparse = Argparse(args=args)
        self.assertEqual(argparse.get('Classical', 'name'), 'Mozart')
        self.assertEqual(argparse.get('Baroque', 'name'), 'Bach')

    def test_method_get_with_mapping(self):
        argparse = Argparse(
            args=args,
            mapping={
                'Classical.name': 'classical_name',
                'Baroque.name': 'baroque_name',
            })
        self.assertEqual(argparse.get('Classical', 'name'), 'Mozart')
        self.assertEqual(argparse.get('Baroque', 'name'), 'Bach')

    def test_exception(self):
        argparse = Argparse(
            args=args,
            mapping={
                'Classical.name': 'classical_name',
                'Baroque.name': 'baroque_name',
                'Romantic.name': 'romantic_name',

            })
        with self.assertRaises(ConfigValueError):
            argparse.get('Romantic', 'name')

        with self.assertRaises(ConfigValueError):
            argparse.get('Modern', 'name')


class TestClassDictionary(unittest.TestCase):

    dictionary = {'Classical': {'name': 'Mozart'}}

    def test_method_get(self):
        dictionary = Dictionary(dictionary=self.dictionary)
        self.assertEqual(dictionary.get('Classical', 'name'), 'Mozart')

    def test_exception(self):
        dictionary = Dictionary(dictionary=self.dictionary)
        with self.assertRaises(ConfigValueError):
            dictionary.get('Romantic', 'name')


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

    def test_non_existent_ini_file(self):
        tmp_path = tempfile.mkdtemp()
        non_existent = os.path.join(tmp_path, 'xxx')
        ini = Ini(path=non_existent)
        with self.assertRaises(ConfigValueError):
            ini.get('lol', 'lol')


# Common code #################################################################


class TestClassReader(unittest.TestCase):

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


class TestFunctionLoadReadersByKeyword(unittest.TestCase):

    def test_without_keywords_arguments(self):
        with self.assertRaises(TypeError):
            load_readers_by_keyword(INI_FILE, 'XXX')

    def test_order_ini_environ(self):
        readers = load_readers_by_keyword(ini=INI_FILE, environ='XXX')
        self.assertEqual(readers[0].__class__.__name__, 'Ini')
        self.assertEqual(readers[1].__class__.__name__, 'Environ')

    def test_order_environ_ini(self):
        readers = load_readers_by_keyword(environ='XXX', ini=INI_FILE, )
        self.assertEqual(readers[0].__class__.__name__, 'Environ')
        self.assertEqual(readers[1].__class__.__name__, 'Ini')


# Integration tests ###########################################################


class TestClassConfigReader(unittest.TestCase):

    def setUp(self):
        # argparser
        parser = argparse.ArgumentParser()
        parser.add_argument('--common-key')
        parser.add_argument('--specific-argparse')
        args = parser.parse_args(
            ['--common-key', 'argparse',
             '--specific-argparse', 'argparse']
        )
        self.argparse = (
            args,
            {'common.key': 'common_key',
                'specific.argparse': 'specific_argparse'}
        )
        # dictionary
        self.dictionary = {'common': {'key': 'dictionary'},
                           'specific': {'dictionary': 'dictionary'}}

        # environ
        self.environ = 'YYY'
        os.environ['YYY__common__key'] = 'environ'
        os.environ['YYY__specific__environ'] = 'environ'

        # ini
        self.ini = os.path.join(FILES_DIR, 'integration.ini')

    def tearDown(self):
        del os.environ['YYY__common__key']
        del os.environ['YYY__specific__environ']

    def test_argparse_first(self):
        config = ConfigReader(
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
            ini=self.ini,
        )
        self.assertEqual(config.common.key, 'argparse')

    def test_dictionary_first(self):
        config = ConfigReader(
            dictionary=self.dictionary,
            argparse=self.argparse,
            environ=self.environ,
            ini=self.ini,
        )
        self.assertEqual(config.common.key, 'dictionary')

    def test_environ_first(self):
        config = ConfigReader(
            environ=self.environ,
            argparse=self.argparse,
            dictionary=self.dictionary,
            ini=self.ini,
        )
        self.assertEqual(config.common.key, 'environ')

    def test_ini_first(self):
        config = ConfigReader(
            ini=self.ini,
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
        )
        self.assertEqual(config.common.key, 'ini')

    def test_specifiy_values(self):
        config = ConfigReader(
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
            ini=self.ini,
        )
        self.assertEqual(config.specific.argparse, 'argparse')
        self.assertEqual(config.specific.dictionary, 'dictionary')
        self.assertEqual(config.specific.environ, 'environ')
        self.assertEqual(config.specific.ini, 'ini')


class TestTypes(unittest.TestCase):

    def setUp(self):
        self.config = ConfigReader(ini=os.path.join(FILES_DIR, 'types.ini'))

    def test_int(self):
        self.assertEqual(self.config.types.int, 1)

    def test_float(self):
        self.assertEqual(self.config.types.float, 1.1)

    def test_str(self):
        self.assertEqual(self.config.types.str, 'Some text')

    def test_list(self):
        self.assertEqual(self.config.types.list, [1, 2, 3])

    def test_tuple(self):
        self.assertEqual(self.config.types.tuple, (1, 2, 3))

    def test_dict(self):
        self.assertEqual(self.config.types.dict, {'one': 1, 'two': 2})

    def test_code(self):
        self.assertEqual(self.config.types.code, 'print(\'lol\')')

    def test_invalid_code(self):
        self.assertEqual(self.config.types.invalid_code, 'print(\'lol)\'')

    def test_bool(self):
        self.assertEqual(self.config.types.bool, True)

    def test_empty_string(self):
        self.assertEqual(self.config.types.empty_str, '')

    def test_none(self):
        self.assertEqual(self.config.types.none, None)

    def test_zero(self):
        self.assertEqual(self.config.types.zero, 0)

    def test_false(self):
        self.assertEqual(self.config.types.false, False)

    def test_false_str(self):
        self.assertEqual(self.config.types.false_str, 'false')
