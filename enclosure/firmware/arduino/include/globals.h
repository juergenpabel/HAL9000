#ifndef __INCLUDE_GLOBAL_H__
#define __INCLUDE_GLOBAL_H__

#include <TFT_eSPI.h>
#include <JPEGDEC.h>
#include <ArduinoJson.h>

#include "device/microcontroller/include.h"
#include "device/board/include.h"
#include "peripherals/mcp23X17/mcp23X17.h"
#include "system/application.h"
#include "util/webserial.h"


extern Microcontroller g_device_microcontroller;
extern Board           g_device_board;

extern TFT_eSPI        g_gui;
extern TFT_eSprite     g_gui_buffer;

extern Application     g_system_application;

extern MCP23X17        g_peripherals_mcp23X17;

extern JPEGDEC         g_util_jpeg;
extern WebSerial       g_util_webserial;

#endif

