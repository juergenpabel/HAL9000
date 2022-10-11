#include "globals.h"


TFT_eSPI     g_gui = TFT_eSPI();
TFT_eSprite  g_gui_overlay = TFT_eSprite(&g_gui);
uint16_t*    g_gui_buffer = NULL;

JPEGDEC      g_gui_util_jpeg;

