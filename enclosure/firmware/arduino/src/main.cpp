#include <FS.h>
#include <LittleFS.h>
#include <TimeLib.h>

#include "globals.h"
#include "device/webserial.h"
#include "system/webserial.h"
#include "peripherals/webserial.h"
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

	if(g_device_board.start() == false) { //TODO: what to do??
		g_system_application.setRunlevel(RunlevelPanicing); //TODO: what to do??
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
	filename  = "/device/board/";
	filename += g_device_board.getIdentifier();
	filename += ".json";
	if(LittleFS.exists(filename.c_str()) == false) {
		error_details  = "board configuration file '(littlefs:)";
		error_details += filename;
		error_details += "' not found";
		g_system_application.processError("panic", "213", "Board error", error_details);
		return;
	}
	file = LittleFS.open(filename.c_str(), "r");
	if(static_cast<bool>(file) == false) {
		error_details  = "failed to open *supposedly existing* '(littlefs:)";
		error_details += filename;
		error_details += "' in read-mode";
		g_system_application.processError("panic", "212", "Filesystem error", error_details);
		return;
	}
	if(deserializeJson(json, file) != DeserializationError::Ok) {
		error_details  = "JSON (syntax) error in board configuration in '(littlefs:)";
		error_details += filename;
		error_details += "'";
		g_system_application.processError("panic", "213", "Board error", error_details);
		file.close();
		return;
	}
	file.close();
	if(g_device_board.configure(json) == false) {
		error_details  = "board '";
		error_details += g_device_board.getIdentifier();
		error_details += "' reported an error applying config from '(littlefs:)";
		error_details += filename;
		error_details += "'";
		g_system_application.processError("panic", "213", "Board error", error_details);
		return;
	}
	if(g_system_application.loadSettings() == false) {
		error_details  = "system failed to load persisted settings from '(littlefs:)";
		error_details += filename;
		error_details += "' (just reflashing littlefs might solve this issue...but not the root cause)";
		g_system_application.processError("panic", "214", "Application error", error_details);
		return;
	}
	g_util_webserial.addCommand("system/runlevel", on_system_runlevel);
	gui_screen_set("animations:system-booting", gui_screen_animations);
}


void loop() {
	static Runlevel      previousRunlevel = RunlevelStarting;
	       Runlevel      currentRunlevel = RunlevelUnknown;

	currentRunlevel = g_system_application.getRunlevel();
	if(currentRunlevel != previousRunlevel) {
		g_util_webserial.send("system/runlevel", g_system_application.getRunlevelName());
		switch(currentRunlevel) {
			case RunlevelConfiguring:
				g_util_webserial.clearCommands();
				g_util_webserial.addCommand("system/runlevel", on_system_runlevel);
				g_util_webserial.addCommand("system/environment", nullptr);
				g_util_webserial.addCommand("system/settings", nullptr);
				g_util_webserial.addCommand("system/features", nullptr);
				g_util_webserial.addCommand("device/microcontroller", nullptr);
				g_util_webserial.addCommand("device/board", nullptr);
				g_util_webserial.addCommand("device/display", nullptr);
				g_util_webserial.addCommand("peripherals/mcp23X17", nullptr);
				g_util_webserial.addCommand("gui/screen", nullptr);
				g_util_webserial.addCommand("gui/overlay", nullptr);
				g_util_webserial.addCommand("*", Application::addConfiguration);
				gui_screen_set("animations:system-starting", gui_screen_animations);
				break;
			case RunlevelReady:
				g_util_webserial.clearCommands();
				g_util_webserial.addCommand("system/runlevel", on_system_runlevel);
				g_util_webserial.addCommand("system/environment", on_system_environment);
				g_util_webserial.addCommand("system/settings", on_system_settings);
				g_util_webserial.addCommand("system/features", on_system_features);
				g_util_webserial.addCommand("gui/screen", on_gui_screen);
				g_util_webserial.addCommand("gui/overlay", on_gui_overlay);
				g_util_webserial.addCommand("device/microcontroller", on_device_microcontroller);
				g_util_webserial.addCommand("device/board", on_device_board);
				g_util_webserial.addCommand("device/display", on_device_display);
				g_util_webserial.addCommand("peripherals/mcp23X17", on_peripherals_mcp23X17);
				g_system_application.applyConfiguration();
				g_system_application.setRunlevel(RunlevelRunning);
				break;
			case RunlevelRunning:
				g_util_webserial.delCommand("device/microcontroller", on_device_microcontroller);
				g_util_webserial.delCommand("device/board", on_device_board);
				g_util_webserial.delCommand("device/display", on_device_display);
				g_util_webserial.delCommand("peripherals/mcp23X17", on_peripherals_mcp23X17);
				break;
			case RunlevelRestarting:
				g_util_webserial.clearCommands();
				g_util_webserial.addCommand("system/runlevel", on_system_runlevel);
				g_util_webserial.addCommand("system/environment", on_system_environment);
				gui_screen_set("animations:system-terminating", gui_screen_animations); //animation triggers reset after last frame
				break;
			case RunlevelHalting:
				g_util_webserial.clearCommands();
				g_util_webserial.addCommand("system/runlevel", on_system_runlevel);
				g_util_webserial.addCommand("system/environment", on_system_environment);
				gui_screen_set("animations:system-terminating", gui_screen_animations); //animation triggers halt after last frame
				break;
			case RunlevelPanicing:
				g_util_webserial.clearCommands();
				g_util_webserial.addCommand("system/runlevel", on_system_runlevel);
				break;
			default:
				g_system_application.processError("panic", "219", "Application error", "Unknown system runlevel (BUG!), panicing");
		}
		previousRunlevel = currentRunlevel;
	}
	if(currentRunlevel == RunlevelRunning) {
		g_peripherals_mcp23X17.check(false);
	}
	g_util_webserial.update();
	gui_update();
}

