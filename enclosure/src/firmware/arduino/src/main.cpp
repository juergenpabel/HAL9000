#include <LittleFS.h>
#include <FS.h>
#include <pico/stdlib.h>
#include <string>
#include <stdexcept>

#include "globals.h"
#include "system/webserial.h"
#include "device/webserial.h"
#include "gui/webserial.h"
#include "system/rp2040.h"
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
			if(Serial) {
				g_util_webserial.send("syslog", "LittleFS error, halting");
			}
			sleep_ms(1000);
		}
	}
	if(g_system_settings.load() == false) {
		g_util_webserial_queue.pushMessage("syslog", "setup() failed to load settings from littlefs");
		g_system_settings.reset();
	}
	if(!Serial) {
		g_system_runtime["gui/screen:splash/filename"] = std::string("error.jpg");
		gui_screen_set(gui_screen_splash);
		while(!Serial) {
			gui_screen_update(false);
			g_system_runtime.update();
			if(g_system_runtime.isAwake()) {
				digitalWrite(TFT_BL, HIGH);
			} else {
				digitalWrite(TFT_BL, LOW);
			}
			sleep_ms(1000);
		}
	}
	g_util_webserial_queue.sendMessages();
	gui_screen_set(gui_screen_idle);

	g_util_webserial.send("syslog", "setup()");
	g_util_webserial.on("system/reset", on_system_reset);
	g_util_webserial.on("system/runtime", on_system_runtime);
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
	g_util_webserial.check();
	g_system_runtime.update();
	if(g_system_runtime.isAwake()) {
		digitalWrite(TFT_BL, HIGH);
		g_util_webserial_queue.sendMessages();
	} else {
		digitalWrite(TFT_BL, LOW);
		g_util_webserial_queue.dropMessages();
	}
	gui_screen_update(false);
	if(g_system_settings.count("system/arduino:loop/sleep_ms") == 1) {
		static int milliseconds = std::stoi(g_system_settings["system/arduino:loop/sleep_ms"]);

		sleep_ms(milliseconds);
	}
}

