#! /usr/bin/env python3

from jflib import Watch

watch = Watch(config_file='/etc/command-watcher.ini', service_name='texlive_update')

tlmgr = '/usr/local/texlive/bin/x86_64-linux/tlmgr'

watch.run('{} update --self'.format(tlmgr))
watch.run('{} update --all'.format(tlmgr))
watch.report(0)
