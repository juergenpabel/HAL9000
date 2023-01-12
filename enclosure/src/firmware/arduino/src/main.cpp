#include <FS.h>
#include <LittleFS.h>
#include <TimeLib.h>

#include "globals.h"
#include "application/webserial.h"
#include "device/webserial.h"
#include "gui/webserial.h"
#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/screen/animations/screen.h"
#include "util/webserial.h"
#include "util/jpeg.h"


void setup() {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> json;
	       etl::string<GLOBAL_FILENAME_SIZE> filename;
	       File                              file;
	       bool                              booting = true;

	g_device_board.start(booting);
	if(booting == true) {
		g_application.setStatus(StatusBooting);
		g_util_webserial.send("syslog/debug", "system was powered on (booting, configuring)");
	} else {
		g_application.setStatus(StatusRunning);
		g_util_webserial.send("syslog/debug", "system was resetted (not booting, running)");
	}
	filename  = "/system/board/";
	filename += g_device_board.getIdentifier();
	filename += "/configuration.json";
	if(LittleFS.exists(filename.c_str()) == true) {
		file = LittleFS.open(filename.c_str(), "r");
		if(deserializeJson(json, file) != DeserializationError::Ok) {
			file.close();
			return;
		}
		file.close();
		if(g_device_board.configure(json.as<JsonVariant>()) == false) {
			return;
		}
	}
	g_gui_buffer = (uint16_t*)malloc(GUI_SCREEN_HEIGHT*GUI_SCREEN_WIDTH*sizeof(uint16_t));
	if(g_gui_buffer == nullptr) {
		while(true) {
			g_util_webserial.send("syslog/fatal", "g_gui_buffer could not be malloc()ed, halting");
			delay(1000);
		}
	}
	g_gui.begin();
	g_gui.setRotation(TFT_ORIENTATION_LOGICAL);
	g_gui.fillScreen(TFT_BLACK);
	g_gui.setTextColor(TFT_WHITE);
	g_gui.setTextFont(1);
	g_gui.setTextSize(5);
	g_gui.setTextDatum(MC_DATUM);
	g_gui_overlay.setColorDepth(1);
	g_gui_overlay.setBitmapColor(TFT_WHITE, TFT_BLACK);
	g_gui_overlay.createSprite(GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT);
	g_gui_overlay.setTextColor(TFT_WHITE, TFT_BLACK, false);
	g_gui_overlay.setTextFont(1);
	g_gui_overlay.setTextSize(2);
	g_gui_overlay.setTextDatum(MC_DATUM);
	g_util_webserial.setCommand("application/runtime", on_application_runtime);
}


void loop() {
	static Status oldStatus = StatusUnknown;
	       Status newStatus = StatusUnknown;

	g_util_webserial.update();
	newStatus = g_application.getStatus();
	if(newStatus != oldStatus) {
		switch(newStatus) {
			case StatusBooting:
				if(gui_screen_get() == gui_screen_none) {
					g_util_webserial.send("application/runtime", "{\"status\":\"booting\"}", false);
					gui_screen_set(gui_screen_animation_startup);
				}
				if(gui_screen_get() == gui_screen_animation_startup) {
					gui_screen_set_refresh();
					newStatus = StatusUnchanged;
				}
				if(gui_screen_get() == gui_screen_idle) {
					g_application.setStatus(StatusConfiguring);
					gui_screen_set(gui_screen_none);
				}
				break;
			case StatusConfiguring:
				if(g_application.hasEnv("application/configuration") == false) {
					g_application.setEnv("application/configuration", "true");
					g_util_webserial.setCommand("*", Application::onConfiguration);
					g_util_webserial.send("application/runtime", "{\"status\":\"configuring\"}", false);
				}
				if(g_application.getEnv("application/configuration").compare("false") == 0) {
					g_application.setStatus(StatusRunning);
					oldStatus = StatusConfiguring;
				}
				newStatus = StatusUnchanged;
				break;
			case StatusRunning:
				g_util_webserial.send("application/runtime", "{\"status\":\"running\"}", false);
				g_util_webserial.setCommand("*", nullptr);
				g_util_webserial.setCommand("application/environment", on_application_environment);
				g_util_webserial.setCommand("application/settings", on_application_settings);
				g_util_webserial.setCommand("device/board", on_device_board);
				g_util_webserial.setCommand("device/microcontroller", on_device_microcontroller);
				g_util_webserial.setCommand("device/mcp23X17", on_device_mcp23X17);
				g_util_webserial.setCommand("device/display", on_device_display);
				g_util_webserial.setCommand("device/sdcard", on_device_sdcard);
				g_util_webserial.setCommand("gui/screen", on_gui_screen);
				g_util_webserial.setCommand("gui/overlay", on_gui_overlay);
				g_application.onRunning();
				break;
			case StatusResetting:
				g_util_webserial.send("application/runtime", "{\"status\":\"resetting\"}", false);
				gui_screen_set(gui_screen_none);
				g_device_board.reset(false);
				break;
			case StatusRebooting:
				g_util_webserial.send("application/runtime", "{\"status\":\"rebooting\"}", false);
				gui_screen_set(gui_screen_animation_shutdown);
				while(gui_screen_get() == gui_screen_animation_shutdown) {
					gui_screen_update(true);
				}
				g_device_board.reset(true);
				break;
			case StatusHalting:
				g_util_webserial.send("application/runtime", "{\"status\":\"halting\"}", false);
				gui_screen_set(gui_screen_animation_shutdown);
				while(gui_screen_get() == gui_screen_animation_shutdown) {
					gui_screen_update(true);
				}
				g_device_board.halt();
				break;
			default:
				g_util_webserial.send("syslog/error", "invalid application status => resetting");
				g_util_webserial.send("application/runtime", "{\"status\":\"resetting\"}", false);
				g_device_board.reset(false);
		}
		if(newStatus != StatusUnchanged) {
			oldStatus = newStatus;
		}
	}
	gui_screen_update(false);
}

