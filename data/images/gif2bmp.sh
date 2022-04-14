#!/bin/bash

rm -rf "active" >> /dev/null
mkdir "active" >> /dev/null
cd "active"
convert -coalesce ../haleye.gif %02d.bmp
mogrify -crop 370x370+85+85 +repage *.bmp
mogrify -resize 240x240 *.bmp
for i in *.bmp ; do convert "$i" -alpha on -background none \( +clone -channel A -evaluate multiply 0 +channel -fill white -draw "ellipse 118,117 120,120 0,360" \)  -compose DstIn -composite "$i" ; done
for i in *.bmp ; do mogrify -background '#000000' -flatten "$i" ; done
for i in *.bmp ; do convert -crop 240x120 $i %d_$i ; done
rm 0_*
for i in 1_*.bmp ; do convert $i +flip 2_$i ; done
for i in 1_*.bmp ; do convert 2_$i $i -append 3_$i ; done
rm 1_*.bmp 2_*.bmp
for i in 3_*.bmp ; do mv $i ${i:4} ; done
cd ..


rm -rf "wakeup" >> /dev/null
mkdir "wakeup" >> /dev/null
cd "wakeup"
for i in {0..9} ; do convert "../active/0$i.bmp" -fill black -colorize $((90-i*10)) 0$i.bmp ; done
cd ..


rm -rf "sleep" >> /dev/null
mkdir "sleep" >> /dev/null
cd "sleep"
for i in {0..9} ; do convert "../active/0$i.bmp" -fill black -colorize $((i*10+10)) 0$i.bmp ; done
cd ..

