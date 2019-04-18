import os
import unittest
from jflib.configurator import Configurator


class TestClassConfiguration(unittest.TestCase):

    def test_environ(self):
        os.environ['AAA_BRIDGE_IP'] = '1.2.3.4'
        os.environ['AAA_BRIDGE_USERNAME'] = 'test'
        config = Configurator(config_environ_prefix='AAA')
        self.assertEqual(config.get('bridge', 'ip'), '1.2.3.4')
        self.assertEqual(config.get('bridge', 'username'), 'test')

    def test_exception(self):
        config = Configurator(config_environ_prefix='AAA')
        with self.assertRaises(ValueError) as cm:
            config.get('lol', 'lol')
        self.assertEqual(
            str(cm.exception),
            'Configuration value could not be found (section “lol” key '
            '“lol”).',
        )
