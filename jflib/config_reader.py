"""
A configuration reader which reads values stored in two levels of keys.
The first level is named `section` and the second level `key`.

argparse arguments (`argparse`): (You have to specify a mapping)

.. code::

    mapping = {
        'section.key': 'args_attribute'
    }

A python dictionary (`dictonary`):

.. code:: python

    {
        'section':  {
            'key': 'value'
        }
    }

Environment variables (`environ`):

.. code:: shell

    export prefix__section__key=value

INI file (`ini`):

.. code:: ini

    [section]
    key = value

"""
import ast
import os
import configparser
import re
import argparse
import abc
import typing


class ConfigValueError(Exception):
    """Configuration value can’t be found."""


class IniReaderError(Exception):
    """Ini file not valid."""


def validate_key(key: str) -> bool:
    """:param key: Validate the name of a section or a key."""
    if re.match(r'^[a-zA-Z0-9_]+$', key):
        return True
    raise ValueError(
        'The key “{}” contains invalid characters (allowed: a-zA-Z0-9_).'
        .format(key)
    )


# Reader classes ##############################################################


class ReaderBase(object, metaclass=abc.ABCMeta):
    """Base class for all readers"""

    def _exception(self, msg):
        """:raises: ConfigValueError"""
        raise ConfigValueError(msg)

    @abc.abstractmethod
    def get(self, section, key):
        raise NotImplementedError('A reader class must have a `get` method.')


class ArgparseReader(ReaderBase):
    """This class tries to read configuration values from a `argparse`
    namespace object. This works fine if your section is one word long
    (`--section-key` = `args.section_key` = `section` + `key`) and not more
    than one word long (`--my-section-key` = `args.my_section_key` = `my` +
    `section_key`). By multi word section you have to specify a mapping
    (`{'my_section.key': 'my_section_key'}`). Without a mapping all sections
    and keys are convert into lowercase (`Section` = `section`).

    :param args: The parsed `argparse` object.
    :param mapping: A dictionary like this one: `{'section.key': 'dest'}`.
      `dest` is the property name of the `args` object.
    """
    def __init__(self, args: argparse.Namespace, mapping: dict = {}):
        self._args = args
        self._mapping = mapping

    def get(self, section: str, key: str) -> typing.Any:
        """
        Get a configuration value stored under a section and a key.

        :param section: Name of the section.
        :param key: Name of the key.

        :raises ConfigValueError: Configuration value couldn’t be found.

        :return: The configuration value stored under a section and a key.
        """
        mapping_key = '{}.{}'.format(section, key)
        if mapping_key in self._mapping:
            argparse_dest = self._mapping[mapping_key]
        else:
            argparse_dest = '{}_{}'.format(section, key).lower()

        if hasattr(self._args, argparse_dest):
            value = getattr(self._args, argparse_dest)
            if value is not None:
                return value

        self._exception('Configuration value could not be found by '
                        'Argparse (section “{}” key “{}”).'
                        .format(section, key))


class DictionaryReader(ReaderBase):
    """Useful for default values.

    :param dictionary: A nested dictionary.
    """
    def __init__(self, dictionary: dict):
        self._dictionary = dictionary

    def get(self, section: str, key: str) -> typing.Any:
        """
        Get a configuration value stored under a section and a key.

        :param section: Name of the section.
        :param key: Name of the key.

        :raises ConfigValueError: Configuration value couldn’t be found.

        :return: The configuration value stored under a section and a key.
        """
        try:
            return self._dictionary[section][key]
        except KeyError:
            self._exception(
                'In the dictionary is no value at dict[{}][{}]'
                .format(section, key)
            )


class EnvironReader(ReaderBase):
    """Read configuration values from environment variables. The name
    of the environment variables have to be in the form `prefix__section__key`.
    Note the two following underscores.

    :param prefix: A enviroment prefix"""

    def __init__(self, prefix: str = None):
        self._prefix = prefix

    def get(self, section: str, key: str) -> typing.Any:
        """
        Get a configuration value stored under a section and a key.

        :param section: Name of the section.
        :param key: Name of the key.

        :raises ConfigValueError: Configuration value couldn’t be found.

        :return: The configuration value stored under a section and a key.
        """
        if self._prefix:
            key = '{}__{}__{}'.format(self._prefix, section, key)
        else:
            key = '{}__{}'.format(section, key)
        if key in os.environ:
            return os.environ[key]
        self._exception('Environment variable not found: {}'.format(key))


class IniReader(ReaderBase):
    """Read configuration files from text files in the INI format.

    :param path: The path of the INI file.
    """
    def __init__(self, path: str):
        self._config = configparser.ConfigParser()
        if not path or not os.path.exists(path):
            raise IniReaderError(
                'Ini configuration path “{}” couldn’t be opened.'
                .format(path)
            )
        self._config.read_file(open(path))

    def get(self, section: str, key: str) -> typing.Any:
        """
        Get a configuration value stored under a section and a key.

        :param section: Name of the section.
        :param key: Name of the key.

        :raises ConfigValueError: Configuration value couldn’t be found.

        :return: The configuration value stored under a section and a key.
        """
        try:
            return self._config[section][key]
        except KeyError:
            self._exception('Configuration value could not be found '
                            '(section “{}” key “{}”).'.format(section, key))


class SpecReader(ReaderBase):
    """Read the default values from the `spec` (specification) dictionary.

    :param spec: The `spec` (specification) dictionary.
    """
    def __init__(self, spec: dict):
        self._spec = spec

    def get(self, section: str, key: str) -> typing.Any:
        """
        Get a configuration value stored under a section and a key.

        :param section: Name of the section.
        :param key: Name of the key.

        :raises ConfigValueError: Configuration value couldn’t be found.

        :return: The configuration value stored under a section and a key.
        """
        try:
            return self._spec[section][key]['default']
        except KeyError:
            self._exception('Configuration value could not be found '
                            '(section “{}” key “{}”).'.format(section, key))


# Common code #################################################################


class ReaderSelector:
    """Select for each get request which reader to use."""

    def __init__(self, *readers):
        self.readers = readers
        """A list of readers."""

    @staticmethod
    def _validate_key(key):
        return validate_key(key)

    def get(self, section: str, key: str):
        """
        Get a configuration value stored under a section and a key.

        :param section: Name of the section.
        :param key: Name of the key.
        """
        self._validate_key(section)
        self._validate_key(key)
        for reader in self.readers:
            try:
                return reader.get(section, key)
            except ConfigValueError:
                pass
        raise ValueError('Configuration value could not be found '
                         '(section “{}” key “{}”).'.format(section, key))


def auto_type(value):
    """https://stackoverflow.com/a/7019325"""
    try:
        return ast.literal_eval(value)
    except ValueError:
        return value
    # ERROR: test_method_send_email_with_config_reader
    # (test_command_watcher.TestClassWatch)
    # AttributeError: 'SyntaxError' object has no attribute 'filename'
    except SyntaxError:
        return value


class DictionaryInterfaceKey:

    def __init__(self, reader, section):
        self._reader = reader
        self._section = section

    def __getitem__(self, name):
        return auto_type(self._reader.get(self._section, name))


class DictionaryInterface:

    def __init__(self, reader):
        self._reader = reader

    def __getitem__(self, name):
        return DictionaryInterfaceKey(self._reader, section=name)


class ClassInterfaceKey:

    def __init__(self, reader, section):
        self._reader = reader
        self._section = section

    def __getattr__(self, name):
        return auto_type(self._reader.get(self._section, name))


class ClassInterface:

    def __init__(self, reader):
        self._reader = reader

    def __getattr__(self, name):
        return ClassInterfaceKey(self._reader, section=name)


def load_readers_by_keyword(**kwargs) -> list:
    """Available readers: `argparse`, `dictionary`, `environ`, `ini`.

    The arguments of this class have to be specified as keyword arguments.
    Each keyword stands for a configuration reader class.
    The order of the keywords is important. The first keyword, more
    specifically the first reader class, overwrites the next ones.

    :param tuple argparse: A tuple `(args, mapping)`.
      `args`: The parsed `argparse` object (Namespace).
      `mapping`: A dictionary like this one: `{'section.key': 'dest'}`. `dest`
      are the propertiy name of the `args` object.
      or only the `argparse` object (Namespace).
    :param dict dictonary: A two dimensional nested dictionary
      `{'section': {'key': 'value'}}`
    :param str environ: The prefix of the environment variables.
    :param str ini: The path of the INI file.
    """
    readers = []
    for keyword, value in kwargs.items():
        if keyword == 'argparse':
            if isinstance(value, tuple) or isinstance(value, list):
                readers.append(ArgparseReader(args=value[0], mapping=value[1]))
            elif value.__class__.__name__ == 'Namespace':
                readers.append(ArgparseReader(args=value))
        elif keyword == 'dictionary':
            readers.append(DictionaryReader(dictionary=value))
        elif keyword == 'environ':
            readers.append(EnvironReader(prefix=value))
        elif keyword == 'ini':
            readers.append(IniReader(path=value))
        elif keyword == 'spec':
            readers.append(SpecReader(spec=value))
    return readers


class ConfigReader(object):
    """Available readers: `argparse`, `dictionary`, `environ`, `ini`.

    The arguments of this class have to be specified as keyword arguments.
    Each keyword stands for a configuration reader class.
    The order of the keywords is important. The first keyword, more
    specifically the first reader class, overwrites the next ones.

    :param spec: A dictionary like this example:

        .. code:: python

            spec = {
                'section_1': {
                    'key_1': {
                        'description': 'Lorem ipsum',
                        'default': 123,
                        'not_empty': True,
                    }
                }
            }

    :param tuple argparse: A tuple `(args, mapping)`.
      `args`: The parsed `argparse` object (Namespace).
      `mapping`: A dictionary like this one: `{'section.key': 'dest'}`. `dest`
      are the propertiy name of the `args` object.
      or only the `argparse` object (Namespace).
    :param dict dictonary: A two dimensional nested dictionary
      `{'section': {'key': 'value'}}`
    :param str environ: The prefix of the environment variables.
    :param str ini: The path of the INI file.
    """
    def __init__(self, spec: dict = {}, **kwargs):
        if spec:
            readers = load_readers_by_keyword(**kwargs, spec=spec)
        else:
            readers = load_readers_by_keyword(**kwargs)
        self.spec = spec
        """The specification dictionary. For more informations look at the
        class arguments of this class."""

        self.reader = ReaderSelector(*readers)
        """:py:class:`ReaderSelector`"""

    def get_class_interface(self) -> ClassInterface:
        return ClassInterface(self.reader)

    def get_dictionary_interface(self) -> DictionaryInterface:
        return DictionaryInterface(self.reader)

    def check_section(self, section, not_empty=False) -> True:
        """Check all keys of a section.

        :raises ValueError: If the value is not configured and can not be
          read by the readers.
        :raises ValueError: If `not_empty` is true and value is empty.
        :raises KeyError: By an unspecify section
        """
        for key, value_spec in self.spec[section].items():
            value = self.reader.get(section, key)
            if 'not_empty' in value_spec and \
               value_spec['not_empty'] and not value:
                raise ValueError('Spec check: section ”{}” key “{}” is empty.'
                                 .format(section, key))
        return True

    def spec_to_argparse(self, parser):
        for section, _ in self.spec.items():
            group = parser.add_argument_group(
                title=section,
                description='Generated by the config_reader.'
            )
            for key, value in self.spec[section].items():
                argument = '--{}-{}'.format(section, key).replace('_', '-')
                kwargs = {}
                if 'description' in value:
                    kwargs['help'] = value['description']
                if 'default' in value:
                    kwargs['default'] = value['default']
                group.add_argument(argument, **kwargs)
