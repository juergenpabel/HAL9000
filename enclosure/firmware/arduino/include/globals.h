#ifndef __INCLUDE_GLOBAL_H__
#define __INCLUDE_GLOBAL_H__

#include <TFT_eSPI.h>
#include <JPEGDEC.h>
#include <ArduinoJson.h>

#include "application/application.h"
#include "device/microcontroller/include.h"
#include "device/board/include.h"
#include "device/mcp23X17/mcp23X17.h"
#include "util/webserial.h"
//TODO:include "device/sdcard/sdcard.h"


extern Microcontroller g_device_microcontroller;
extern Board           g_device_board;
extern MCP23X17        g_device_mcp23X17;

extern TFT_eSPI        g_gui;
extern TFT_eSprite     g_gui_screen;
extern TFT_eSprite     g_gui_overlay;

extern JPEGDEC         g_util_jpeg;
extern WebSerial       g_util_webserial;

extern Application     g_application;


#endif

