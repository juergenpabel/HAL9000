#!/bin/bash

convert "$1" \( -clone 0 -fill "#000000" -colorize 100 \) \( -clone 0,1 -compose difference -composite -separate +channel -evaluate-sequence max -auto-level \) -delete 1 -alpha off -compose over -compose copy_opacity -composite "$1"

