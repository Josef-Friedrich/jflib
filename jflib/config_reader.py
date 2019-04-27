"""
A configuration reader which reads values stored in two levels of keys.
The first level is named `section` and the second level `key`.

INI file (`ini`):

.. code:: ini

    [section]
    key = value

Environment variables (`environ`):

.. code:: shell

    export prefix__section__key=value

argparse arguments (`argparse`): (You have to specify a mapping)

.. code::

    mapping = {
        'section.key': 'args_attribute'
    }

"""
import ast
import os
import configparser
import re


class ConfigValueError(Exception):
    """Configuration value can’t be found."""


def validate_key(key):
    if re.match(r'^[a-zA-Z0-9_]+$', key):
        return True
    raise ValueError(
        'The key “{}” contains invalid characters (allowed: a-zA-Z0-9_).'
        .format(key)
    )


# Reader classes ##############################################################


class ReaderBase:
    """Base class for all readers"""

    def _exception(self, msg):
        raise ConfigValueError(msg)


class Argparse(ReaderBase):
    """
    :param obj args: The parsed `argparse` object.
    :param dict mapping: A dictionary like this one: `{'section.key': 'dest'}`.
      `dest` are the propertiy name of the `args` object.
    """

    def __init__(self, args, mapping):
        self._args = args
        self._mapping = mapping

    def get(self, section, key):
        """
        Get a configuration value stored under a section and a key.

        :param string section: Name of the section.
        :param string key: Name of the key.

        :return: The configuration value stored under a section and a key.
        """
        mapping_key = '{}.{}'.format(section, key)
        try:
            argparse_dest = self._mapping[mapping_key]
        except KeyError:
            msg = 'Mapping key “{}” for an argparse destination not found.'
            self._exception(msg.format(mapping_key))
        try:
            return getattr(self._args, argparse_dest)
        except AttributeError:
            self._exception('Configuration value could not be found by '
                            'Argparse (section “{}” key “{}”).'
                            .format(section, key))


class Environ(ReaderBase):

    def __init__(self, prefix=None):
        self._prefix = prefix

    def get(self, section, key):
        """
        Get a configuration value stored under a section and a key.

        :param string section: Name of the section.
        :param string key: Name of the key.

        :return: The configuration value stored under a section and a key.
        """
        if self._prefix:
            key = '{}__{}__{}'.format(self._prefix, section, key)
        else:
            key = '{}__{}'.format(section, key)
        if key in os.environ:
            return os.environ[key]
        self._exception('Environment variable not found: {}'.format(key))


class Ini(ReaderBase):

    def __init__(self, path):
        self._config = configparser.ConfigParser()
        self._config.read(path)

    def get(self, section, key):
        """
        Get a configuration value stored under a section and a key.

        :param string section: Name of the section.
        :param string key: Name of the key.
        """
        try:
            return self._config[section][key]
        except KeyError:
            self._exception('Configuration value could not be found '
                            '(section “{}” key “{}”).'.format(section, key))


# Common code #################################################################


class Reader:

    def __init__(self, *readers):
        self.readers = readers

    @staticmethod
    def _validate_key(key):
        return validate_key(key)

    def get(self, section, key):
        self._validate_key(section)
        self._validate_key(key)
        for reader in self.readers:
            try:
                return reader.get(section, key)
            except ConfigValueError:
                pass
        raise ValueError('Configuration value could not be found '
                         '(section “{}” key “{}”).'.format(section, key))


class Value:

    def __init__(self, reader, section):
        self._reader = reader
        self._section = section

    def _auto_type(self, value):
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

    def __getattr__(self, name):
        return self._auto_type(self._reader.get(self._section, name))


def load_readers_by_keyword(**kwargs):
    """Available readers: `argparse`, `environ`, `ini`.

    The arguments of this class have to be specified as keyword arguments.
    Each keyword stands for a configuration reader class.
    The order of the keywords is important. The last keyword, more
    specifically the last reader class, overwrites the previous ones.

    :param tuple argparse: A tuple `(args, mapping)`.
      `args`: The parsed `argparse` object.
      `mapping`: A dictionary like this one: `{'section.key': 'dest'}`. `dest`
      are the propertiy name of the `args` object.
    :param str environ: The prefix of the environment variables.
    :param str ini: The path of the INI file.
    """
    readers = []
    for keyword, value in kwargs.items():
        if keyword == 'ini':
            readers.append(Ini(path=value))
        elif keyword == 'environ':
            readers.append(Environ(prefix=value))
        elif keyword == 'argparse':
            readers.append(Argparse(args=value[0], mapping=value[1]))

    return readers


class ConfigReader(object):
    """Available readers: `argparse`, `environ`, `ini`.

    The arguments of this class have to be specified as keyword arguments.
    Each keyword stands for a configuration reader class.
    The order of the keywords is important. The last keyword, more
    specifically the last reader class, overwrites the previous ones.

    :param tuple argparse: A tuple `(args, mapping)`.
      `args`: The parsed `argparse` object.
      `mapping`: A dictionary like this one: `{'section.key': 'dest'}`. `dest`
      are the propertiy name of the `args` object.
    :param str environ: The prefix of the environment variables.
    :param str ini: The path of the INI file.
    """
    def __init__(self, **kwargs):
        readers = load_readers_by_keyword(**kwargs)
        self._reader = Reader(*readers)

    def __getattr__(self, name):
        return Value(self._reader, section=name)
