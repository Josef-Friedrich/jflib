#! /usr/bin/env python3

import re

from jflib import Watch
from jflib.utils import download, make_executable

watch = Watch(config_file='/etc/command-watcher.ini', service_name='hblock')

URL = 'https://raw.githubusercontent.com/hectorm/hblock/master/hblock'
DEST = '/usr/local/bin/hblock'

download(URL, DEST)
watch.log.info('Download file “{}” from “{}”'.format(DEST, URL))

make_executable(DEST)
watch.log.info('Make file “{}” executable.'.format(DEST))

watch.run('/usr/local/bin/hblock')

stdout = watch.stdout

match = re.search(r'(\d+) blocked domains!', stdout)
blocklist_count = match.group(1)
sources_count = stdout.count(
    'https://raw.githubusercontent.com/hectorm/hmirror'
)

watch.report(
    status=0,
    perfdata={'blocklist_count': blocklist_count,
              'sources_count': sources_count}
)
