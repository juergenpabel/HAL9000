#include <TimeLib.h>
#include <TFT_eSPI.h>
#include <LittleFS.h>
#include <pngle.h>
#include <SPI.h>
#include <FS.h>
#include <RingBuf.h>
#include <SimpleWebSerial.h>
#include <pico/stdlib.h>

#include "globals.h"
#include "system/webserial.h"
#include "device/webserial.h"
#include "gui/webserial.h"

#include "system/rp2040.h"
#include "system/settings.h"
#include "device/mcp23X17/mcp23X17.h"
#include "gui/screen/screen.h"
#include "gui/screen/splash/jpeg.h"


TFT_eSPI        g_tft = TFT_eSPI();
TFT_eSprite     g_tft_overlay = TFT_eSprite(&g_tft);
MCP23X17        g_mcp23X17;
SimpleWebSerial g_webserial;
WebSerialQueue  g_webserial_queue;
Settings        g_settings;


void setup() {
	Serial.begin(115200);
	pinMode(TFT_BL, OUTPUT);
	digitalWrite(TFT_BL, LOW);
	g_tft.begin();
	g_tft.setRotation(2);
	g_tft.fillScreen(TFT_BLACK);
	g_tft.setTextColor(TFT_WHITE, TFT_BLACK);
	g_tft.setTextFont(1);
	g_tft.setTextDatum(TC_DATUM);
	g_tft.setTextSize(3);
	g_tft_overlay.createSprite(160, 20);
	g_tft_overlay.setTextFont(1);
	g_tft_overlay.setTextDatum(TC_DATUM);
	g_tft_overlay.setTextSize(2);

	if(LittleFS.begin() == false) {
		while(1) {
			g_webserial.send("syslog", "LittleFS error, halting");
			sleep_ms(1000);
		}
	}
	if(g_settings.load("/system/configuration.bson") == false) {
		LittleFS.remove("/system/configuration.bson");
	}
	if(!Serial) {
		splash_jpeg("/images/splash/error.jpg");
		digitalWrite(TFT_BL, HIGH);
		while(!Serial) {
			sleep_ms(100);
		}
		g_tft.fillScreen(TFT_BLACK);
		digitalWrite(TFT_BL, LOW);
	}
	g_webserial.send("syslog", "setup()");
	g_webserial.on("system/reset", on_system_reset);
	g_webserial.on("system/settings", on_system_settings);
	g_webserial.on("system/time", on_system_time);
	g_webserial.on("device/sdcard", on_device_sdcard);
	g_webserial.on("device/mcp23X17", on_device_mcp23X17);
	g_webserial.on("device/display", on_device_display);
	g_webserial.on("gui/screen", on_gui_screen);
	g_webserial.on("gui/overlay", on_gui_overlay);
	g_webserial.send("syslog", "loop()");

	digitalWrite(TFT_BL, HIGH); //TODO:backlighting off logic
}


void loop() {
	if(!Serial) {
		rp2040_reset();
	}
	g_webserial_queue.sendMessages();
	g_webserial.check();
	screen_update(NULL, false);
	sleep_ms(g_settings["arduino:loop-sleep_ms"].toInt());
}

