#!/usr/bin/env python3

from shutil import copytree as shutil_copytree

shutil_copytree('./resources/images/frontend/animations', './data/images/animations', dirs_exist_ok=True)
shutil_copytree('./resources/images/frontend/overlays',   './data/images/overlays', dirs_exist_ok=True)
shutil_copytree('./resources/system',                     './data/system', dirs_exist_ok=True)

