#!/usr/bin/env python3

from shutil import copytree as shutil_copytree, \
                   ignore_patterns as shutil_ignore_patterns

shutil_copytree('./resources/system',            './data/system', dirs_exist_ok=True, ignore=shutil_ignore_patterns('README.md', 'LICENSE'))
shutil_copytree('./resources/device',            './data/device', dirs_exist_ok=True, ignore=shutil_ignore_patterns('README.md', 'LICENSE'))
shutil_copytree('./resources/gui',               './data/gui',    dirs_exist_ok=True, ignore=shutil_ignore_patterns('README.md', 'LICENSE'))
shutil_copytree('./resources/images/animations', './data/images/animations', dirs_exist_ok=True, ignore=shutil_ignore_patterns('README.md', 'LICENSE'))

