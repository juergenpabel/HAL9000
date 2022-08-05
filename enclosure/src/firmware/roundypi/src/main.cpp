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
#include "filesystem/webserial.h"
#include "mcp23X17/webserial.h"
#include "display/webserial.h"
#include "gui/webserial.h"
#include "system/rp2040.h"
#include "system/settings.h"
#include "mcp23X17/mcp23X17.h"
#include "gui/screen.h"
#include "gui/overlay.h"
#include "gui/jpeg.h"


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
			g_webserial.warn("LittleFS error, halting");
			sleep_ms(1000);
		}
	}
	if(g_settings.load("/system/configuration.bson") == false) {
		g_settings["arduino:loop-sleep_ms"] =  "0";
		g_settings["audio:volume-mute"] =  "FALSE";
		g_settings["audio:volume-minimum"] =   "0";
		g_settings["audio:volume-current"] =  "50";
		g_settings["audio:volume-maximum"] = "100";
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
	g_webserial.send("RoundyPI", "setup()");
	g_webserial.on("system:reset", on_system_reset);
	g_webserial.on("system:settings", on_system_settings);
	g_webserial.on("system:time", on_system_time);
	g_webserial.on("filesystem:flash", on_filesystem_flash);
	g_webserial.on("filesystem:sdcard", on_filesystem_sdcard);
	g_webserial.on("display:backlight", on_display_backlight);
	g_webserial.on("mcp23X17:setup", on_mcp23X17_setup);
	g_webserial.on("mcp23X17:loop", on_mcp23X17_loop);
	g_webserial.on("screen:sequence", on_screen_sequence);
	g_webserial.on("screen:splash", on_screen_splash);
	g_webserial.send("RoundyPI", "Webserial ready");
	g_webserial.send("RoundyPI", "loop()");
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

