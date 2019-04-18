import os
import configparser


class Configurator(object):

    def __init__(self, config_file_path=None,
                 config_environ_prefix=None):
        """
        :param str config_file_path: The path of the configuration file.
          The default value is `~/.lively-lights.ini`.
        :param str config_environ_prefix: The environment variable prefix
          `lively_lights` should look for configuration, by default
          `LIVELY_LIGHTS_`.
        """

        if not config_file_path:
            config_file_path = '~/.lively-lights.ini'
        if not config_environ_prefix:
            config_environ_prefix = 'LIVELY_LIGHTS'

        self.config_path = os.path.expanduser(config_file_path)
        self.environ_prefix = config_environ_prefix
        if os.path.exists(self.config_path):
            self.config = configparser.ConfigParser()
            self.config.read(self.config_path)

    def _envrion_key(self, section, key):
        return '{}_{}_{}'.format(self.environ_prefix, section.upper(),
                                 key.upper())

    def get(self, section, key):
        value = None
        envrion_key = self._envrion_key(section, key)
        if envrion_key in os.environ:
            value = os.environ[envrion_key]
        elif hasattr(self, 'config') and section in self.config and \
                key in self.config[section]:
            value = self.config[section][key]

        if value:
            try:
                converted_value = float(value)
                return converted_value
            except ValueError:
                return value

        else:
            raise ValueError('Configuration value could not be found '
                             '(section “{}” key “{}”).'.format(section, key))
