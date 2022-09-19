#ifndef __ROUNDYPI_GLOBAL_H__
#define __ROUNDYPI_GLOBAL_H__

#include <FS.h>
#include <JPEGDEC.h>
#include <TFT_eSPI.h>
#include <ArduinoJson.h>

#include "system/microcontroller/include.h"
#include "system/runtime.h"
#include "system/settings.h"
#include "device/sdcard/sdcard.h"
#include "device/mcp23X17/mcp23X17.h"
#include "util/webserial.h"


extern Microcontroller g_system_microcontroller;
extern Runtime         g_system_runtime;
extern Settings        g_system_settings;
extern MCP23X17        g_device_mcp23X17;
extern SDCard          g_device_sdcard;
extern TFT_eSPI        g_device_tft;
extern TFT_eSprite     g_device_tft_overlay;
extern uint16_t*       g_gui_tft_buffer;
extern JPEGDEC         g_util_jpeg;
extern WebSerial       g_util_webserial;


#endif

