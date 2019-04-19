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


class Environ(object):

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


class Ini(object):

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


class Argparse(object):

    def __init__(self, args, mapping):
        pass

    def get(self, section, key):
        """
        Get a configuration value stored under a section and a key.

        :param string section: Name of the section.
        :param string key: Namve of the key.

        :return: The configuration value stored under a section and a key.
        """


class Reader:

    def __init__(self, *readers):
        self.readers = readers

    def get(self, section, key):
        validate_key(section)
        validate_key(key)
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


class ConfigReader(object):
    """
    :param str config_file_path: The path of the configuration file.
    :param str environ_prefix: A environment variable prefix for  all
        environment variables.
    """

    def __init__(self, *readers):
        self._reader = Reader(*readers)

    def __getattr__(self, name):
        return ObjectAttributeInterfaceLevel2(self._reader, section=name)
