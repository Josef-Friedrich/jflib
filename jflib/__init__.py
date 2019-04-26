from ._version import get_versions  # noqa: F401
from .argparser_to_readme import argparser_to_readme  # noqa: F401
from .capturing import Capturing  # noqa: F401
from .command_watcher import Watch  # noqa: F401
from .config_reader import ConfigReader  # noqa: F401
from .send_email import send_email  # noqa: F401
from .termcolor import colored, cprint  # noqa: F401

__version__ = get_versions()['version']
del get_versions
