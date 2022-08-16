#include "globals.h"


TFT_eSPI        g_gui_tft = TFT_eSPI();
TFT_eSprite     g_gui_tft_overlay = TFT_eSprite(&g_gui_tft);
uint16_t        g_gui_tft_buffer[TFT_HEIGHT*TFT_WIDTH];
JPEGDEC         g_gui_util_jpeg;

