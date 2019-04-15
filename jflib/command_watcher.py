import logging
import queue
import re
import subprocess
import threading

from . import termcolor


class StreamAndMemoryHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)
        self._records = []

    @staticmethod
    def _print_colorized(record):
        match = re.search(r'([0-9_]+):([A-Z]+):(.*)', record)
        time = match.group(1)
        level = match.group(2)
        msg = match.group(3)

        if level == 'DEBUG':
            color = 'grey'
        elif level == 'INFO':
            color = 'white'
        elif level == 'WARNING':
            color = 'yellow'
        elif level == 'ERROR':
            color = 'red'
        else:
            color = 'white'
        print('{}:{}:{}'.format(
            time,
            termcolor.colored(level.ljust(8), color, attrs=['reverse']),
            msg,
        ))

    def emit(self, record):
        record = self.format(record)
        self._records.append(record)
        self._print_colorized(record)

    def __str__(self):
        return '\n'.join(self._records)


class Watch:

    def __init__(self, command):
        self.log = logging.getLogger(__name__)
        self.log_handler = StreamAndMemoryHandler()
        formatter = logging.Formatter(
            fmt='%(asctime)s_%(msecs)03d:%(levelname)s:%(message)s',
            datefmt='%Y%m%d_%H%M%S',
        )
        self.log_handler.setFormatter(formatter)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(self.log_handler)
        self.queue = queue.Queue()
        self.command = command

    def _stdout_stderr_reader(self, pipe, channel):
        try:
            with pipe:
                for line in iter(pipe.readline, b''):
                    self.queue.put((line, channel))
        finally:
            self.queue.put(None)

    def _start_thread(self, pipe, channel):
        threading.Thread(
            target=self._stdout_stderr_reader,
            args=[pipe, channel]
        ).start()

    def run(self):
        process = subprocess.Popen(self.command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=1)

        self._start_thread(process.stdout, 'stdout')
        self._start_thread(process.stderr, 'stderr')

        for _ in range(2):
            for line, channel in iter(self.queue.get, None):
                if line:
                    line = line.decode('utf-8').strip()

                if line:
                    if channel == 'stderr':
                        self.log.error(line)
                    if channel == 'stdout':
                        self.log.debug(line)

        process.wait()
        return process

