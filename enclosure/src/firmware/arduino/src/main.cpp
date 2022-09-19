#include <LittleFS.h>
#include <FS.h>
#include <TimeLib.h>

#include "globals.h"
#include "system/webserial.h"
#include "device/webserial.h"
#include "gui/webserial.h"
#include "system/system.h"
#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/screen/animations/screen.h"

#include "util/webserial.h"
#include "util/jpeg.h"


void setup() {
	system_start();
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
			delay(1000);
		}
	}
	if(g_system_settings.load() == false) {
		g_util_webserial.send("syslog", "setup() failed to load settings from littlefs");
		g_system_settings.reset();
	}
	g_system_runtime.update();
	if(g_system_runtime.isAsleep()) {
		digitalWrite(TFT_BL, LOW);
	}
	if(year() < 2001) {
		gui_screen_set(gui_screen_animation_startup);
		while(gui_screen_get() == gui_screen_animation_startup) {
			gui_screen_update(g_system_runtime.isAwake());
		}
	}
	if(!Serial) {
		g_system_runtime["gui/screen:splash/filename"] = "error.jpg";
		gui_screen_set(gui_screen_splash);
		while(!Serial) {
			gui_screen_update(false);
			g_system_runtime.update();
			if(g_system_runtime.isAwake()) {
				digitalWrite(TFT_BL, HIGH);
			} else {
				digitalWrite(TFT_BL, LOW);
			}
			delay(1000);
		}
	}
	gui_screen_set(gui_screen_idle);
	g_util_webserial.update();

	g_util_webserial.send("syslog", "setup()");
	g_util_webserial.set("system/reset", on_system_reset);
	g_util_webserial.set("system/microcontroller", on_system_microcontroller);
	g_util_webserial.set("system/runtime", on_system_runtime);
	g_util_webserial.set("system/settings", on_system_settings);
	g_util_webserial.set("system/time", on_system_time);
	g_util_webserial.set("device/sdcard", on_device_sdcard);
	g_util_webserial.set("device/mcp23X17", on_device_mcp23X17);
	g_util_webserial.set("device/display", on_device_display);
	g_util_webserial.set("gui/screen", on_gui_screen);
	g_util_webserial.set("gui/overlay", on_gui_overlay);
	g_util_webserial.send("syslog", "loop()");
}


void loop() {
	if(!Serial) {
		if(gui_screen_get() != gui_screen_animation_shutdown) {
			system_reset();
		}
		while(gui_screen_get() == gui_screen_animation_shutdown) {
			gui_screen_update(g_system_runtime.isAwake());
		}
		system_halt();
	}
	g_util_webserial.update();
	g_system_runtime.update();
	if(g_system_runtime.isAwake()) {
		digitalWrite(TFT_BL, HIGH);
	} else {
		digitalWrite(TFT_BL, LOW);
	}
	gui_screen_update(false);
	if(g_system_settings.count("system/arduino:loop/sleep_ms") == 1) {
		static int milliseconds = atoi(g_system_settings["system/arduino:loop/sleep_ms"].c_str());

		delay(milliseconds);
	}
}

