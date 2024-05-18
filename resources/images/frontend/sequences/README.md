# HAL9000 animation

The images used by this project are derived from a source image,
which has been created by Jean-Claude Heudin. He gave permission
to use, modify and distribute his file for the purposes of this project.

The animated source image (haleye.gif) was copied from:
http://www.jcheudin.fr/playground/playground/hal9000/images/haleye.gif

For some other HAL9000 fun, check out his HAL9000 interactive game:
http://www.jcheudin.fr/playground/playground/hal9000/

The script gif2jpeg.sh converts the animated GIF into JPEGs that are used
for different animation sequences (./frames/...). 
- wakeup: fades from black to image
- active: single images from original GIF (modified as described below), used in a loop while active
- sleep: fades from image to black
The JPEGs are numbered and stored in corresponding subdirectories.

The following modifications of the original image are implemented by
the script:
- separate GIF animation into individual images
- cut out only the (red'ish) eye (without the silver frame)
- mirror the bottom half to the top in order to remove the reflections
  (because the enclosure features a fisheye dome, this adds reflections
  "naturally")

