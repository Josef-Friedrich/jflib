import logging
import queue
import re
import subprocess
import threading
import uuid

from . import termcolor

# CRITICAL 50
# ERROR 40
# WARNING 30
# INFO 20
# DEBUG 10
# NOTSET 0
STDERR = 35
logging.addLevelName(STDERR, 'STDERR')
STDOUT = 5
logging.addLevelName(STDOUT, 'STDOUT')


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
        elif level in ('ERROR', 'STDERR'):
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
        # To get a fresh logger on each watch action.
        self.log = logging.getLogger(name=str(uuid.uuid1()))
        self.log_handler = StreamAndMemoryHandler()
        formatter = logging.Formatter(
            fmt='%(asctime)s_%(msecs)03d:%(levelname)s:%(message)s',
            datefmt='%Y%m%d_%H%M%S',
        )
        self.log_handler.setFormatter(formatter)
        self.log.setLevel(STDOUT)
        self.log.addHandler(self.log_handler)
        self.queue = queue.Queue()
        self.command = command

    def _stdout_stderr_reader(self, pipe, stream):
        try:
            with pipe:
                for line in iter(pipe.readline, b''):
                    self.queue.put((line, stream))
        finally:
            self.queue.put(None)

    def _start_thread(self, pipe, stream):
        threading.Thread(
            target=self._stdout_stderr_reader,
            args=[pipe, stream]
        ).start()

    def run(self):
        process = subprocess.Popen(self.command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=1)

        self._start_thread(process.stdout, 'stdout')
        self._start_thread(process.stderr, 'stderr')

        for _ in range(2):
            for line, stream in iter(self.queue.get, None):
                if line:
                    line = line.decode('utf-8').strip()

                if line:
                    if stream == 'stderr':
                        self.log.log(STDERR, line)
                    if stream == 'stdout':
                        self.log.log(STDOUT, line)

        process.wait()
        return process

