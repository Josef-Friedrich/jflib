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


class ReaderBase:
    """Base class for all readers"""


class Environ(ReaderBase):

    def __init__(self, prefix=None):
        self._prefix = prefix

    def get(self, section, key):
        """
        Get a configuration value stored under a section and a key.

        :param string section: Name of the section.
        :param string key: Namve of the key.

        :return: The configuration value stored under a section and a key.
        """
        if self._prefix:
            key = '{}__{}__{}'.format(self._prefix, section, key)
        else:
            key = '{}__{}'.format(section, key)
        if key in os.environ:
            return os.environ[key]
        raise ConfigValueError('Environment variable not found: {}'
                               .format(key))


class Ini(ReaderBase):

    def __init__(self, path):
        self._config = configparser.ConfigParser()
        self._config.read(path)

    def get(self, section, key):
        """
        Get a configuration value stored under a section and a key.

        :param string section: Name of the section.
        :param string key: Namve of the key.
        """
        try:
            return self._config[section][key]
        except KeyError:
            raise ConfigValueError('Configuration value could not be found '
                                   '(section “{}” key “{}”).'.format(section,
                                                                     key))


class Argparse(ReaderBase):

    def __init__(self, args, mapping):
        self._args = args
        self._mapping = mapping

    def get(self, section, key):
        """
        Get a configuration value stored under a section and a key.

        :param string section: Name of the section.
        :param string key: Namve of the key.

        :return: The configuration value stored under a section and a key.
        """
        return getattr(self._args, self._mapping['{}.{}'.format(section, key)])


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


class ObjectAttributeInterfaceLevel2:

    def __init__(self, reader, section):
        self._reader = reader
        self._section = section

    def __getattr__(self, name):
        return self._reader.get(self._section, name)


def load_readers_by_keyword(**kwargs):
    readers = []
    for keyword, value in kwargs.items():
        if keyword == 'ini':
            readers.append(Ini(path=value))
        elif keyword == 'environ':
            readers.append(Environ(prefix=value))
    return readers


class ConfigReader(object):
    """Available readers: `ini`, `environ`, `argparse`

    Have to be specified as keyword arguments. The order of the keywords is
    important. The last keyword overwrites to the other.

    :param str ini: The path of the INI file.
    :param str environ: The prefix of the environment variables.
    :param str argparse: The parsed `argparse` object.
    """
    def __init__(self, **kwargs):
        readers = load_readers_by_keyword(**kwargs)
        self._reader = Reader(*readers)

    def __getattr__(self, name):
        return ObjectAttributeInterfaceLevel2(self._reader, section=name)
