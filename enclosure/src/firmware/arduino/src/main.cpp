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
	g_gui.begin();
	g_gui.setRotation(2);
	g_gui.fillScreen(TFT_BLACK);
	g_gui.setTextColor(TFT_WHITE);
	g_gui.setTextFont(1);
	g_gui.setTextSize(5);
	g_gui.setTextDatum(MC_DATUM);
	g_gui_overlay.setColorDepth(1);
	g_gui_overlay.setBitmapColor(TFT_WHITE, TFT_BLACK);
	g_gui_overlay.createSprite(TFT_WIDTH, TFT_HEIGHT);
	g_gui_overlay.setTextColor(TFT_WHITE, TFT_BLACK, false);
	g_gui_overlay.setTextFont(1);
	g_gui_overlay.setTextSize(2);
	g_gui_overlay.setTextDatum(MC_DATUM);
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
	g_system_runtime["system/state:conciousness"] = "awake";
	g_system_runtime.update();
	if(g_system_runtime.isAsleep()) {
		g_device_board.displayOff();
	}
	if(g_system_runtime["system/state:app/target"].compare("booting") == 0) {
		gui_screen_set(gui_screen_animation_startup);
		while(gui_screen_get() == gui_screen_animation_startup) {
			gui_screen_update(g_system_runtime.isAwake());
		}
	}
	if(!Serial) {
		g_system_runtime["system/state:app/target"] = "waiting";
		g_system_runtime["gui/screen:splash/filename"] = "error.jpg";
		gui_screen_set(gui_screen_splash);
		while(!Serial) {
			gui_screen_update(false);
			g_system_runtime.update();
			if(g_system_runtime.isAwake()) {
				g_device_board.displayOn();
			} else {
				g_device_board.displayOff();
			}
			delay(1000);
		}
	}
	g_system_runtime["system/state:app/target"] = "running";
	gui_screen_set(gui_screen_idle);
	g_util_webserial.update();

	g_util_webserial.send("syslog", "setup()");
	g_util_webserial.set("system/app", on_system_app);
	g_util_webserial.set("system/mcu", on_system_mcu);
	g_util_webserial.set("system/time", on_system_time);
	g_util_webserial.set("system/runtime", on_system_runtime);
	g_util_webserial.set("system/settings", on_system_settings);
	g_util_webserial.set("device/sdcard", on_device_sdcard);
	g_util_webserial.set("device/mcp23X17", on_device_mcp23X17);
	g_util_webserial.set("device/display", on_device_display);
	g_util_webserial.set("gui/screen", on_gui_screen);
	g_util_webserial.set("gui/overlay", on_gui_overlay);
	g_util_webserial.send("syslog", "loop()");
}


void loop() {
	if(!Serial) {
		etl::string<GLOBAL_VALUE_SIZE>& app_target = g_system_runtime["system/state:app/target"];

		if(app_target.compare("rebooting") == 0 || app_target.compare("halting") == 0) {
			gui_screen_set(gui_screen_animation_shutdown);
			while(gui_screen_get() == gui_screen_animation_shutdown) {
				gui_screen_update(g_system_runtime.isAwake());
			}
			if(g_system_runtime["system/state:app/target"].compare("halting") == 0) {
				system_halt();
			}
		}
		system_reset();
	}
	g_util_webserial.update();
	g_system_runtime.update();
	if(g_system_runtime.isAwake()) {
		g_device_board.displayOn();
	} else {
		g_device_board.displayOff();
	}
	gui_screen_update(false);
	if(g_system_settings.count("system/arduino:loop/sleep_ms") == 1) {
		static int milliseconds = atoi(g_system_settings["system/arduino:loop/sleep_ms"].c_str());

		delay(milliseconds);
	}
}

