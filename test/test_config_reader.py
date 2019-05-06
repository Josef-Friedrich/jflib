import os
import unittest
import argparse
import tempfile

from jflib import config_reader
from jflib.config_reader import \
    ArgparseReader, \
    ConfigReader, \
    ConfigValueError, \
    DictionaryReader, \
    EnvironReader, \
    IniReader, \
    load_readers_by_keyword, \
    ReaderSelector, \
    ReaderBase, \
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
ARGPARSER_NAMESPACE = parser.parse_args(['--baroque-name', 'Bach',
                                         '--classical-name', 'Mozart'])


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


class FalseReader(ReaderBase):

    def not_get(self):
        return 'It’s not get'


class TestClassReaderBase(unittest.TestCase):

    def test_exception(self):
        with self.assertRaises(TypeError):
            FalseReader()  # pylint: disable=abstract-class-instantiated


class TestClassArgparseReader(unittest.TestCase):

    def test_method_get_without_mapping(self):
        argparse = ArgparseReader(args=ARGPARSER_NAMESPACE)
        self.assertEqual(argparse.get('Classical', 'name'), 'Mozart')
        self.assertEqual(argparse.get('Baroque', 'name'), 'Bach')

    def test_method_get_with_mapping(self):
        argparse = ArgparseReader(
            args=ARGPARSER_NAMESPACE,
            mapping={
                'Classical.name': 'classical_name',
                'Baroque.name': 'baroque_name',
            })
        self.assertEqual(argparse.get('Classical', 'name'), 'Mozart')
        self.assertEqual(argparse.get('Baroque', 'name'), 'Bach')

    def test_exception(self):
        argparse = ArgparseReader(
            args=ARGPARSER_NAMESPACE,
            mapping={
                'Classical.name': 'classical_name',
                'Baroque.name': 'baroque_name',
                'Romantic.name': 'romantic_name',

            })
        with self.assertRaises(ConfigValueError):
            argparse.get('Romantic', 'name')

        with self.assertRaises(ConfigValueError):
            argparse.get('Modern', 'name')


class TestClassDictionaryReader(unittest.TestCase):

    dictionary = {'Classical': {'name': 'Mozart'}}

    def test_method_get(self):
        dictionary = DictionaryReader(dictionary=self.dictionary)
        self.assertEqual(dictionary.get('Classical', 'name'), 'Mozart')

    def test_exception(self):
        dictionary = DictionaryReader(dictionary=self.dictionary)
        with self.assertRaises(ConfigValueError):
            dictionary.get('Romantic', 'name')


class TestClassEnvironReader(unittest.TestCase):

    def test_method_get(self):
        os.environ['AAA__bridge__ip'] = '1.2.3.4'
        os.environ['AAA__bridge__username'] = 'test'
        environ = EnvironReader(prefix='AAA')
        self.assertEqual(environ.get('bridge', 'ip'), '1.2.3.4')
        self.assertEqual(environ.get('bridge', 'username'), 'test')

    def test_exception(self):
        environ = EnvironReader(prefix='AAA')
        with self.assertRaises(ConfigValueError) as cm:
            environ.get('lol', 'lol')
        self.assertEqual(
            str(cm.exception),
            'Environment variable not found: AAA__lol__lol',
        )


class TestClassEnvironWithoutPrefix(unittest.TestCase):

    def test_method_get(self):
        os.environ['Avantgarde__name'] = 'Stockhausen'
        environ = EnvironReader()
        self.assertEqual(environ.get('Avantgarde', 'name'), 'Stockhausen')
        del os.environ['Avantgarde__name']

    def test_exception(self):
        environ = EnvironReader()
        with self.assertRaises(ConfigValueError) as cm:
            environ.get('xxxAvantgarde', 'xxxname')
        self.assertEqual(
            str(cm.exception),
            'Environment variable not found: xxxAvantgarde__xxxname',
        )


class TestClassIniReader(unittest.TestCase):

    def test_method_get(self):
        ini = IniReader(path=INI_FILE)
        self.assertEqual(ini.get('Classical', 'name'), 'Mozart')
        self.assertEqual(ini.get('Romantic', 'name'), 'Schumann')

    def test_exception(self):
        ini = IniReader(path=INI_FILE)
        with self.assertRaises(ConfigValueError) as context:
            ini.get('lol', 'lol')
        self.assertEqual(
            str(context.exception),
            'Configuration value could not be found (section “lol” key '
            '“lol”).',
        )

    def test_non_existent_ini_file(self):
        tmp_path = tempfile.mkdtemp()
        non_existent = os.path.join(tmp_path, 'xxx')
        with self.assertRaises(config_reader.IniReaderError):
            IniReader(path=non_existent)

    def test_none(self):
        with self.assertRaises(config_reader.IniReaderError):
            IniReader(path=None)

    def test_false(self):
        with self.assertRaises(config_reader.IniReaderError):
            IniReader(path=False)

    def test_emtpy_string(self):
        with self.assertRaises(config_reader.IniReaderError):
            IniReader(path='')


# Common code #################################################################


class TestClassReaderSelector(unittest.TestCase):

    def test_ini_first(self):
        reader = ReaderSelector(IniReader(INI_FILE),
                                EnvironReader(prefix='XXX'))
        self.assertEqual(reader.get('Classical', 'name'), 'Mozart')

    def test_environ_first(self):
        reader = ReaderSelector(EnvironReader('XXX'), IniReader(INI_FILE))
        self.assertEqual(reader.get('Baroque', 'name'), 'Bach')

    def test_exception(self):
        reader = ReaderSelector(EnvironReader('XXX'), IniReader(INI_FILE))
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
            load_readers_by_keyword(INI_FILE, 'XXX')  # pylint: disable=E1121

    def test_order_ini_environ(self):
        readers = load_readers_by_keyword(ini=INI_FILE, environ='XXX')
        self.assertEqual(readers[0].__class__.__name__, 'IniReader')
        self.assertEqual(readers[1].__class__.__name__, 'EnvironReader')

    def test_order_environ_ini(self):
        readers = load_readers_by_keyword(environ='XXX', ini=INI_FILE, )
        self.assertEqual(readers[0].__class__.__name__, 'EnvironReader')
        self.assertEqual(readers[1].__class__.__name__, 'IniReader')

    def test_argparse_single_arguemnt(self):
        readers = load_readers_by_keyword(argparse=ARGPARSER_NAMESPACE)
        self.assertEqual(readers[0].__class__.__name__, 'ArgparseReader')


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
        config_reader = ConfigReader(
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
            ini=self.ini,
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.common.key, 'argparse')

    def test_argparse_empty(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--empty-key')
        args = parser.parse_args([])
        config_reader = ConfigReader(
            argparse=(args, {}),
            dictionary={'empty': {'key': 'from_dict'}},
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.empty.key, 'from_dict')

    def test_dictionary_first(self):
        config_reader = ConfigReader(
            dictionary=self.dictionary,
            argparse=self.argparse,
            environ=self.environ,
            ini=self.ini,
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.common.key, 'dictionary')

    def test_environ_first(self):
        config_reader = ConfigReader(
            environ=self.environ,
            argparse=self.argparse,
            dictionary=self.dictionary,
            ini=self.ini,
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.common.key, 'environ')

    def test_ini_first(self):
        config_reader = ConfigReader(
            ini=self.ini,
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.common.key, 'ini')

    def test_specifiy_values(self):
        config_reader = ConfigReader(
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
            ini=self.ini,
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.specific.argparse, 'argparse')
        self.assertEqual(config.specific.dictionary, 'dictionary')
        self.assertEqual(config.specific.environ, 'environ')
        self.assertEqual(config.specific.ini, 'ini')

    def test_method_get_class_interface(self):
        config_reader = ConfigReader(
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
            ini=self.ini,
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.specific.argparse, 'argparse')
        self.assertEqual(config.specific.dictionary, 'dictionary')
        self.assertEqual(config.specific.environ, 'environ')
        self.assertEqual(config.specific.ini, 'ini')

    def test_method_get_dictionary_interface(self):
        config_reader = ConfigReader(
            argparse=self.argparse,
            dictionary=self.dictionary,
            environ=self.environ,
            ini=self.ini,
        )
        config = config_reader.get_dictionary_interface()
        self.assertEqual(config['specific']['argparse'], 'argparse')
        self.assertEqual(config['specific']['dictionary'], 'dictionary')
        self.assertEqual(config['specific']['environ'], 'environ')
        self.assertEqual(config['specific']['ini'], 'ini')

    def test_method_check_section(self):
        dictionary = {
            'missing_key': {
                'key': 'value'
            },
            'all_good': {
                'key': 'value'
            },
            'empty': {
                'key': ''
            }
        }
        spec = {
            'missing_key': {  # section
                'key': {  # key
                    'not_empty': True,
                },
                'not_configured_key': {  # key
                    'not_empty': False,
                },
            },
            'all_good': {  # section
                'key': {  # key
                    'not_empty': True,
                }
            },
            'empty': {  # section
                'key': {  # key
                    'not_empty': True,
                }
            }
        }
        config_reader = ConfigReader(
            spec=spec,
            dictionary=dictionary,
        )
        self.assertTrue(config_reader.check_section('all_good'))
        with self.assertRaises(ValueError):
            config_reader.check_section('missing_key')
        with self.assertRaises(KeyError):
            config_reader.check_section('xxx')
        with self.assertRaises(ValueError):
            config_reader.check_section('empty')

    def test_spec_defaults(self):
        dictionary = {
            'no_default': {
                'key': 'No default value',
            },
        }
        spec = {
            'default': {
                'key': {
                    'description': 'A default value',
                    'default': 123,
                },
            },
            'no_default': {
                'key': {
                    'description': 'No default value',
                },
            },
        }
        config_reader = ConfigReader(
            spec=spec,
            dictionary=dictionary,
        )
        config = config_reader.get_class_interface()
        self.assertEqual(config.no_default.key, 'No default value')
        self.assertEqual(config.default.key, 123)

    def test_method_spec_to_argparse(self):
        spec = {
            'email': {
                'smtp_login': {
                    'description': 'The SMTP login name',
                    'default': 'user1',
                },
            },
        }
        config_reader = ConfigReader(spec=spec)
        parser = argparse.ArgumentParser()
        config_reader.spec_to_argparse(parser)
        args = parser.parse_args([])
        self.assertEqual(args.email_smtp_login, 'user1')
        args = parser.parse_args(['--email-smtp-login', 'user2'])
        self.assertEqual(args.email_smtp_login, 'user2')


class TestTypes(unittest.TestCase):

    def setUp(self):
        config_reader = ConfigReader(ini=os.path.join(FILES_DIR, 'types.ini'))
        self.config = config_reader.get_class_interface()

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
