#ifndef __ROUNDYPI_GLOBAL_H__
#define __ROUNDYPI_GLOBAL_H__

#include <TFT_eSPI.h>
#include <SimpleWebSerial.h>
#include <JPEGDEC.h>
#include <PNGdec.h>
#include "system/settings.h"
#include "device/mcp23X17/mcp23X17.h"
#include "util/queue.h"


extern PNG             g_gui_png;
extern JPEGDEC         g_gui_jpeg;
extern TFT_eSPI        g_gui_tft;
extern TFT_eSprite     g_gui_tft_overlay;
extern SimpleWebSerial g_util_webserial;
extern WebSerialQueue  g_util_webserial_queue;
extern Settings        g_system_settings;
extern MCP23X17        g_device_mcp23X17;


#endif

