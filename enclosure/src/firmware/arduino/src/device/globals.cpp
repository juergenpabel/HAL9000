#include "globals.h"


TFT_eSPI     g_device_tft = TFT_eSPI();
TFT_eSprite  g_device_tft_overlay = TFT_eSprite(&g_device_tft);
SDCard       g_device_sdcard;
MCP23X17     g_device_mcp23X17;

