import os
import configparser


class ConfigValueError(Exception):
    """Configuration value can’t be found."""


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


class ConfigReader(object):
    """
    :param str config_file_path: The path of the configuration file.
    :param str environ_prefix: A environment variable prefix for  all
        environment variables.
    """

    def __init__(self, config_file=None, environ_prefix=None):
        self._config_file = None
        self._config_ini = None
        if config_file:
            self._config_file = os.path.expanduser(config_file)
            if os.path.exists(self._config_file):
                self._config_ini = configparser.ConfigParser()
                self._config_ini.read(self._config_file)
        self._environ_prefix = environ_prefix

    def _envrion_key(self, section, key):
        return '{}__{}__{}'.format(self._environ_prefix, section, key)

    def get(self, section, key):
        envrion_key = self._envrion_key(section, key)
        if envrion_key in os.environ:
            return os.environ[envrion_key]
        elif hasattr(self, '_config_ini') and \
                self._config_ini and \
                section in self._config_ini and \
                key in self._config_ini[section]:
            return self._config_ini[section][key]

        else:
            raise ValueError('Configuration value could not be found '
                             '(section “{}” key “{}”).'.format(section, key))
