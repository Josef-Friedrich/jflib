import unittest

from jflib import \
    argparser_to_readme, \
    Capturing, \
    colored, \
    ConfigReader, \
    cprint, \
    send_email, \
    Watch


class TestImports(unittest.TestCase):

    def test_argparser_to_readme(self):
        self.assertTrue(callable(argparser_to_readme))

    def test_capturing(self):
        self.assertTrue(callable(Capturing))

    def test_colored(self):
        self.assertTrue(callable(colored))

    def test_config_reader(self):
        self.assertTrue(callable(ConfigReader))

    def test_cprint(self):
        self.assertTrue(callable(cprint))

    def test_send_email(self):
        self.assertTrue(callable(send_email))

    def test_watch(self):
        self.assertTrue(callable(Watch))
