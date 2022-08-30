#include <LittleFS.h>
#include <FS.h>
#include <pico/stdlib.h>

#include "globals.h"
#include "system/webserial.h"
#include "device/webserial.h"
#include "gui/webserial.h"
#include "system/rp2040.h"
#include "system/settings.h"
#include "device/mcp23X17/mcp23X17.h"
#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/splash/screen.h"


void setup() {
	system_rp2040_start();
	g_gui_tft.begin();
	g_gui_tft.setRotation(2);
	g_gui_tft.fillScreen(TFT_BLACK);
	g_gui_tft.setTextColor(TFT_WHITE);
	g_gui_tft.setTextFont(1);
	g_gui_tft.setTextSize(5);
	g_gui_tft.setTextDatum(MC_DATUM);
	g_gui_tft_overlay.setColorDepth(1);
	g_gui_tft_overlay.setBitmapColor(TFT_WHITE, TFT_BLACK);
	g_gui_tft_overlay.createSprite(TFT_WIDTH, TFT_HEIGHT);
	g_gui_tft_overlay.setTextColor(TFT_WHITE, TFT_BLACK, false);
	g_gui_tft_overlay.setTextFont(1);
	g_gui_tft_overlay.setTextSize(2);
	g_gui_tft_overlay.setTextDatum(MC_DATUM);

	if(LittleFS.begin() == false) {
		while(1) {
			g_util_webserial.send("syslog", "LittleFS error, halting");
			sleep_ms(1000);
		}
	}
	if(g_system_settings.load("/system/configuration.bson") == false) {
		LittleFS.remove("/system/configuration.bson");
	}
	if(!Serial) {
		g_system_status["gui/screen:splash/filename"] = "error.jpg";
		gui_screen_set(gui_screen_splash);
		while(!Serial) {
			g_system_status.update();
			if(g_system_status.isAwake()) {
				digitalWrite(TFT_BL, HIGH);
			} else {
				digitalWrite(TFT_BL, LOW);
			}
			sleep_ms(1000);
		}
	}
	gui_screen_set(gui_screen_idle);

	g_util_webserial.send("syslog", "setup()");
	g_util_webserial.on("system/reset", on_system_reset);
	g_util_webserial.on("system/settings", on_system_settings);
	g_util_webserial.on("system/time", on_system_time);
	g_util_webserial.on("device/sdcard", on_device_sdcard);
	g_util_webserial.on("device/mcp23X17", on_device_mcp23X17);
	g_util_webserial.on("device/display", on_device_display);
	g_util_webserial.on("gui/screen", on_gui_screen);
	g_util_webserial.on("gui/overlay", on_gui_overlay);
	g_util_webserial.send("syslog", "loop()");
}


void loop() {
	if(!Serial) {
		system_rp2040_reset();
	}
	g_util_webserial_queue.sendMessages();
	g_util_webserial.check();
	g_system_status.update();
	if(g_system_status.isAwake()) {
		digitalWrite(TFT_BL, HIGH);
	} else {
		digitalWrite(TFT_BL, LOW);
	}
	gui_screen_update(false);
	sleep_ms(std::stoi(g_system_settings["system/arduino:loop/sleep_ms"]));
}
