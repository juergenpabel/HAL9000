#include "globals.h"


PNG             g_gui_png;
JPEGDEC         g_gui_jpeg;
TFT_eSPI        g_gui_tft = TFT_eSPI();
TFT_eSprite     g_gui_tft_overlay = TFT_eSprite(&g_gui_tft);

