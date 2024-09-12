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
#include "gui/overlay/overlay.h"
#include "gui/webserial.h"
#include "util/webserial.h"
#include "util/jpeg.h"


void setup() {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> json;
	static etl::string<GLOBAL_VALUE_SIZE>    error_details;
	static etl::string<GLOBAL_FILENAME_SIZE> filename;
	       File                              file;

	if(g_device_board.start() == false) {
		g_application.setStatus(StatusPanicing);
		gui_screen_set("none", gui_screen_none);
		gui_overlay_set("none", gui_overlay_none);
		return;
	}
	g_gui.begin();
	g_gui.setRotation(TFT_ORIENTATION_LOGICAL);
	g_gui.fillScreen(TFT_BLACK);
	g_gui_buffer.setColorDepth(16);
	g_gui_buffer.createSprite(GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT);
	if(g_gui_buffer.getPointer() == nullptr) {
		g_util_webserial.send("syslog/warning", "out-of-memory: UI running without frame buffer (reduced graphics)");
	}
	filename  = "/system/board/";
	filename += g_device_board.getIdentifier();
	filename += "/configuration.json";
	if(LittleFS.exists(filename.c_str()) == false) {
		g_application.setStatus(StatusPanicing);
		error_details  = "board configuration file (littlefs:)'";
		error_details += filename;
		error_details += "' not found";
		g_application.notifyError("critical", "213", "Board error", error_details);
		return;
	}
	file = LittleFS.open(filename.c_str(), "r");
	if(file == false) {
		g_application.setStatus(StatusPanicing);
		error_details  = "failed to open *supposedly existing* (littlefs:)'";
		error_details += filename;
		error_details += "' in read-mode";
		g_application.notifyError("critical", "212", "Filesystem error", error_details);
		return;
	}
	if(deserializeJson(json, file) != DeserializationError::Ok) {
		g_application.setStatus(StatusPanicing);
		error_details  = "JSON (syntax) error in board configuration in (littlefs:)'";
		error_details += filename;
		error_details += "'";
		g_application.notifyError("critical", "213", "Board error", error_details);
		file.close();
		return;
	}
	file.close();
	if(g_device_board.configure(json) == false) {
		g_application.setStatus(StatusPanicing);
		error_details  = "board '";
		error_details += g_device_board.getIdentifier();
		error_details += "' reported an error applying config from (littlefs:)'";
		error_details += filename;
		error_details += "'";
		g_application.notifyError("critical", "213", "Board error", error_details);
		return;
	}
	if(g_application.loadSettings() == false) {
		g_application.setStatus(StatusPanicing);
		error_details  = "application failed to load persisted settings from (littlefs:)'";
		error_details += filename;
		error_details += "' (just reflashing littlefs might solve this issue...but not the root cause)";
		g_application.notifyError("critical", "214", "Application error", error_details);
		return;
	}
	g_application.setStatus(StatusConfiguring);
	g_util_webserial.setCommand("application/runtime", on_application_runtime);
	gui_screen_set("startup", gui_screen_animations_startup);
}


void loop() {
	static unsigned long configurationTimeout = 0;
	static Status        previousStatus = StatusStarting;
	       Status        currentStatus = StatusUnknown;

	g_device_mcp23X17.check(false);
	g_util_webserial.update();
	currentStatus = g_application.getStatus();
	if(currentStatus != previousStatus) {
		etl::string<GLOBAL_VALUE_SIZE> payloadStatus("{\"status\":{\"name\":\"<STATUS>\"}}");

		g_util_webserial.send("application/runtime", payloadStatus.replace(19, 8, g_application.getStatusName()), false);
		switch(currentStatus) {
			case StatusConfiguring:
				if(g_application.hasSetting("application/runtime:configuration/timeout") == true) {
					configurationTimeout = atoi(g_application.getSetting("application/runtime:configuration/timeout").c_str());
				}
				if(configurationTimeout == 0) {
					configurationTimeout = APPLICATION_CONFIGURATION_TIMEOUT_MS;
				}
				configurationTimeout += millis();
				g_util_webserial.setCommand("application/environment", nullptr);
				g_util_webserial.setCommand("application/settings", nullptr);
				g_util_webserial.setCommand("device/board", nullptr);
				g_util_webserial.setCommand("device/microcontroller", nullptr);
				g_util_webserial.setCommand("device/mcp23X17", nullptr);
				g_util_webserial.setCommand("device/display", nullptr);
				g_util_webserial.setCommand("gui/screen", nullptr);
				g_util_webserial.setCommand("gui/overlay", nullptr);
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
				g_util_webserial.setCommand("gui/screen", on_gui_screen);
				g_util_webserial.setCommand("gui/overlay", on_gui_overlay);
				Application::onConfiguration(Application::Null, JsonVariant());
				break;
			case StatusRebooting:
				g_util_webserial.setCommand(Application::Null, nullptr);
				g_util_webserial.setCommand("application/runtime", on_application_runtime);
				gui_screen_set("shutdown", gui_screen_animations_shutdown); //animation triggers reset after last frame
				while(true) {
					g_util_webserial.update();
					gui_update();
				}
			case StatusHalting:
				g_util_webserial.setCommand(Application::Null, nullptr);
				g_util_webserial.setCommand("application/runtime", on_application_runtime);
				gui_screen_set("shutdown", gui_screen_animations_shutdown); //animation triggers halt after last frame
				while(true) {
					g_util_webserial.update();
					gui_update();
				}
			case StatusPanicing:
				g_util_webserial.setCommand(Application::Null, nullptr);
				g_util_webserial.setCommand("application/runtime", on_application_runtime);
				gui_update();
				while(true) {
					g_util_webserial.update();
				}
			default:
				g_util_webserial.setCommand(Application::Null, nullptr);
				while(true) {
					g_util_webserial.send("syslog/critical", "BUG: invalid/unknown application status", true, true);
					g_util_webserial.send("application/runtime", "{\"status\":\"unknown\"}", false, true);
					delay(1000);
				}
		}
		previousStatus = currentStatus;
	}
	if(currentStatus == StatusConfiguring) {
		if(configurationTimeout > 0 && millis() > configurationTimeout) {
			g_application.notifyError("critical", "210", "No connection to host", "failed to establish communications with service 'frontend' (via USB)");
			configurationTimeout = 0;
		}
	}
	gui_update();
}

