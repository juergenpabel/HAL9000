#include <FS.h>
#include <LittleFS.h>

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
#include "system/system.h"


void setup() {
	System::start();
	System::configure();
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
					g_util_webserial.send("application/runtime", "{\"status\": \"booting\"}");
					gui_screen_set(gui_screen_animation_startup);
				}
				if(gui_screen_get() == gui_screen_animation_startup) {
					gui_screen_set_refresh();
					newStatus = StatusUnchanged;
				}
				if(gui_screen_get() == gui_screen_idle) {
					g_application.setStatus(StatusConfiguring);
				}
				break;
			case StatusConfiguring:
				if(g_application.hasEnv("application/configuration") == false) {
					g_util_webserial.send("application/runtime", "{\"status\": \"configuring\"}");
					g_application.setEnv("application/configuration", "true");
					g_util_webserial.setCommand("*", Application::onConfiguration);
				}
				if(g_application.getEnv("application/configuration").compare("false") == 0) {
					g_application.setStatus(StatusRunning);
					oldStatus = StatusConfiguring;
				}
				newStatus = StatusUnchanged;
				break;
			case StatusRunning:
				g_util_webserial.send("application/runtime", "{\"status\": \"running\"}");
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
				gui_screen_set(gui_screen_idle);
				break;
			case StatusResetting:
				g_util_webserial.send("application/runtime", "{\"status\": \"resetting\"}");
				System::reset();
				break;
			case StatusRebooting:
				g_util_webserial.send("application/runtime", "{\"status\": \"rebooting\"}");
				gui_screen_set(gui_screen_animation_shutdown);
				while(gui_screen_get() == gui_screen_animation_shutdown) {
					gui_screen_update(true);
				}
				System::reset();
				break;
			case StatusHalting:
				g_util_webserial.send("application/runtime", "{\"status\": \"halting\"}");
				gui_screen_set(gui_screen_animation_shutdown);
				while(gui_screen_get() == gui_screen_animation_shutdown) {
					gui_screen_update(true);
				}
				System::halt();
				break;
			default:
				g_util_webserial.send("syslog/error", "invalid application status => resetting");
				System::reset();
		}
		if(newStatus != StatusUnchanged) {
			oldStatus = newStatus;
		}
	}
	gui_screen_update(false);
}

