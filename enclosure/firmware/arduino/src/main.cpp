#include <FS.h>
#include <LittleFS.h>
#include <TimeLib.h>

#include "globals.h"
#include "application/webserial.h"
#include "device/webserial.h"
#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/screen/animations/screen.h"
#include "gui/webserial.h"
#include "util/webserial.h"
#include "util/jpeg.h"


void setup() {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> json;
	       etl::string<GLOBAL_FILENAME_SIZE> filename;
	       File                              file;
	       bool                              booting = true;

	g_device_board.start(booting);
	if(booting == true) {
		g_util_webserial.send("syslog/debug", "system was hard-resetted or powered-on (starting => configuring => waiting => ready => running)");
		g_application.setStatus(StatusStarting);
	} else {
		g_util_webserial.send("syslog/debug", "system was soft-resetted (starting => running)");
		g_application.setStatus(StatusRunning);
	}
	filename  = "/system/board/";
	filename += g_device_board.getIdentifier();
	filename += "/configuration.json";
	if(LittleFS.exists(filename.c_str()) == true) {
		file = LittleFS.open(filename.c_str(), "r");
		if(deserializeJson(json, file) != DeserializationError::Ok) {
			g_application.notifyError("error", "12", "Configuration error", filename);
			json.clear();
		}
		file.close();
	}
	if(json.isNull() == false) {
		if(g_device_board.configure(json) == false) {
			g_application.notifyError("error", "12", "Configuration error", g_device_board.getIdentifier());
		}
	}
	g_gui.begin();
	g_gui.setRotation(TFT_ORIENTATION_LOGICAL);
	g_gui.fillScreen(TFT_BLACK);
	g_gui_screen.setColorDepth(16);
	g_gui_screen.createSprite(GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT);
	if(g_gui_screen.getPointer() == nullptr) {
		g_util_webserial.send("syslog/warning", "out-of-memory: UI running without screen-sprite (no 'real' graphics)");
		g_application.notifyError("warn", "11", "Disabled animations", "g_gui_screen.createSprite() failed");
	}
	g_gui_overlay.setColorDepth(8);
	g_gui_overlay.createSprite(GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT);
	if(g_gui_overlay.getPointer() == nullptr) {
		g_util_webserial.send("syslog/warning", "out-of-memory: UI running without overlay-sprite");
		g_application.notifyError("warn", "11", "Disabled overlays", "g_gui_overlay.createSprite() failed");
	}
}


void loop() {
	static unsigned long configurationTimeout = 0;
	static Status        previousStatus = StatusUnknown;
	       Status        currentStatus = StatusUnknown;

	g_util_webserial.update();
	currentStatus = g_application.getStatus();
	if(currentStatus != previousStatus) {
		etl::string<GLOBAL_VALUE_SIZE> payloadStatus("{\"status\":{\"name\":\"<STATUS>\"}}");

		g_util_webserial.send("application/runtime", payloadStatus.replace(19, 8, g_application.getStatusName()), false);
		switch(currentStatus) {
			case StatusStarting:
				if(g_application.loadSettings() == false) {
					g_util_webserial.send("syslog/critical", "failed to load application settings, will probably be non-functional");
				}
				gui_screen_set("", gui_screen_animations_startup);
				g_application.setStatus(StatusConfiguring);
				g_util_webserial.setCommand("application/runtime", on_application_runtime);
				break;
			case StatusConfiguring:
				configurationTimeout = millis() + 90000; //TODO:config option
				g_util_webserial.setCommand("*", Application::onConfiguration);
				break;
			case StatusReady:
				configurationTimeout = 0;
				g_util_webserial.setCommand("*", nullptr);
				g_util_webserial.setCommand("application/environment", on_application_environment);
				g_util_webserial.setCommand("application/settings", on_application_settings);
				break;
			case StatusRunning:
				g_util_webserial.setCommand("device/board", on_device_board);
				g_util_webserial.setCommand("device/microcontroller", on_device_microcontroller);
				g_util_webserial.setCommand("device/mcp23X17", on_device_mcp23X17);
				g_util_webserial.setCommand("device/display", on_device_display);
				g_util_webserial.setCommand("device/sdcard", on_device_sdcard);
				g_util_webserial.setCommand("gui/screen", on_gui_screen);
				g_util_webserial.setCommand("gui/overlay", on_gui_overlay);
				Application::onConfiguration(Application::Null, JsonVariant());
				break;
			case StatusResetting:
				gui_screen_set("none", gui_screen_none);
				g_device_board.reset(false);
				break;
			case StatusRebooting:
				gui_screen_set("", gui_screen_animations_shutdown);
				while(gui_screen_get() == gui_screen_animations) {
					gui_screen_update(true);
				}
				g_device_board.reset(true);
				break;
			case StatusHalting:
				gui_screen_set("", gui_screen_animations_shutdown);
				while(gui_screen_get() == gui_screen_animations) {
					gui_screen_update(true);
				}
				g_device_board.halt();
				break;
			default:
				g_util_webserial.send("syslog/error", "invalid application status => resetting");
				g_util_webserial.send("application/runtime", "{\"status\":\"resetting\"}", false);
				g_device_board.reset(false);
		}
		previousStatus = currentStatus;
	}
	if(configurationTimeout > 0 && millis() > configurationTimeout) {
		Error error("error", "01", "No connection to host", "ERROR #01");

		g_util_webserial.send(error.level.insert(0, "syslog/"), error.message); // TODO: + " => " + error.detail);
		g_application.setEnv("gui/screen:error/id", error.id);
		g_application.setEnv("gui/screen:error/message", error.message);
		gui_screen_set("error", gui_screen_error);
		configurationTimeout = 0;
	}
	gui_update();
	if(currentStatus == StatusRunning) {
		static TickType_t    previousTicks = 0;
		       TickType_t    currentTicks;

		currentTicks = xTaskGetTickCount();
		if((currentTicks-previousTicks) < pdMS_TO_TICKS(50)) {
			vTaskDelay(pdMS_TO_TICKS(50) - (currentTicks-previousTicks));
		}
		previousTicks = currentTicks;
	}
}

