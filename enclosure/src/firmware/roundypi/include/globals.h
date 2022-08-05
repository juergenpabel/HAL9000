#ifndef __ROUNDYPI_GLOBAL_H__
#define __ROUNDYPI_GLOBAL_H__

#include <TFT_eSPI.h>
#include <SimpleWebSerial.h>
#include "system/settings.h"
#include "webserial/queue.h"
#include "mcp23X17/mcp23X17.h"




extern TFT_eSPI        g_tft;
extern TFT_eSprite     g_tft_overlay;
extern SimpleWebSerial g_webserial;
extern WebSerialQueue  g_webserial_queue;
extern Settings        g_settings;
extern MCP23X17        g_mcp23X17;


#endif

