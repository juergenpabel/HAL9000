#include <FS.h>
#include <LittleFS.h>
#include <TimeLib.h>

#include "globals.h"
#include "application/webserial.h"
#include "device/webserial.h"
#include "gui/webserial.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
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
			g_application.notifyError("error", "002", "JSON error in board configuration", 60);
			json.clear();
		}
		file.close();
	}
	if(json.isNull() == false) {
		if(g_device_board.configure(json) == false) {
			g_application.notifyError("error", "003", "Failed to apply board configuration", 60);
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
	g_gui_buffer = (uint16_t*)malloc(GUI_SCREEN_HEIGHT*GUI_SCREEN_WIDTH*sizeof(uint16_t));
	if(g_gui_buffer == nullptr) {
		g_application.notifyError("warn", "001", "Not enough RAM: animations off", 10);
	}
	g_util_webserial.setCommand("application/runtime", on_application_runtime);
}


void loop() {
	static unsigned long timeout_offline = 0;
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
					g_application.loadSettings();
					g_util_webserial.setCommand("*", Application::onConfiguration);
					g_util_webserial.send("application/runtime", "{\"status\":\"configuring\"}", false);
					timeout_offline = millis() + 10000; //TODO:config option
				}
				if(g_application.getEnv("application/configuration").compare("false") == 0) {
					g_application.setEnv("application/configuration", Application::Null);
					g_application.setStatus(StatusRunning);
					oldStatus = StatusConfiguring;
					timeout_offline = 0;
				}
				if(timeout_offline > 0 && millis() > timeout_offline) {
					const char* error_code = "01";
					const char* error_message = "No connection to host";

					g_application.setEnv("gui/screen:error/code", error_code);
					g_application.setEnv("gui/screen:error/message", error_message);
					g_application.setEnv("gui/screen:error/timeout", "0");
					g_util_webserial.send("syslog/error", error_message);
					gui_screen_set(gui_screen_error);
					timeout_offline = 0;
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

