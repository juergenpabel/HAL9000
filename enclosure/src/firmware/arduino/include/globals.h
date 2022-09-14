#ifndef __ROUNDYPI_GLOBAL_H__
#define __ROUNDYPI_GLOBAL_H__

#include <TFT_eSPI.h>
#include <JPEGDEC.h>
#include <ArduinoJson.h>
#include "system/runtime.h"
#include "system/settings.h"
#include "device/mcp23X17/mcp23X17.h"
#include "util/webserial.h"


extern Runtime         g_system_runtime;
extern Settings        g_system_settings;
extern MCP23X17        g_device_mcp23X17;
extern TFT_eSPI        g_gui_tft;
extern TFT_eSprite     g_gui_tft_overlay;
extern uint16_t        g_gui_tft_buffer[TFT_WIDTH*TFT_HEIGHT];
extern JPEGDEC         g_util_jpeg;
extern WebSerial       g_util_webserial;



#endif

