#include "globals.h"


TFT_eSPI     g_gui = TFT_eSPI();
TFT_eSprite  g_gui_screen = TFT_eSprite(&g_gui);
TFT_eSprite  g_gui_overlay = TFT_eSprite(&g_gui);

JPEGDEC      g_gui_util_jpeg;

