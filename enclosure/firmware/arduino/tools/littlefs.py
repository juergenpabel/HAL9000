#!/usr/bin/env python3

from shutil import copytree as shutil_copytree, \
                   ignore_patterns as shutil_ignore_patterns

shutil_copytree('./resources/images/frontend/animations', './data/images/animations', dirs_exist_ok=True, ignore=shutil_ignore_patterns('README.md', 'LICENSE'))
shutil_copytree('./resources/images/frontend/overlays',   './data/images/overlays', dirs_exist_ok=True, ignore=shutil_ignore_patterns('README.md', 'LICENSE'))
shutil_copytree('./resources/system',                     './data/system', dirs_exist_ok=True, ignore=shutil_ignore_patterns('README.md', 'LICENSE'))

