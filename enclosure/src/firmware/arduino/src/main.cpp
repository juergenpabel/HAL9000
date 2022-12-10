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
	if(g_system_settings.load() == false) {
		g_util_webserial.send("syslog/error", "setup() failed to load settings from littlefs");
		g_system_settings.reset();
	}
	g_util_webserial.set("system/application", on_system_application);
	g_util_webserial.set("system/microcontroller", on_system_microcontroller);
	g_util_webserial.set("system/time", on_system_time);
	g_util_webserial.set("system/runtime", on_system_runtime);
	g_util_webserial.set("system/settings", on_system_settings);
	g_util_webserial.set("device/sdcard", on_device_sdcard);
	g_util_webserial.set("device/mcp23X17", on_device_mcp23X17);
	g_util_webserial.set("device/display", on_device_display);
	g_util_webserial.set("gui/screen", on_gui_screen);
	g_util_webserial.set("gui/overlay", on_gui_overlay);
}


void loop() {
	static int oldStatus = StatusUnknown;
	       int newStatus = StatusUnknown;

	g_util_webserial.update();
	g_system_runtime.update();
	newStatus = g_system_runtime.getStatus();
	if(newStatus != oldStatus) {
		switch(newStatus) {
			case StatusBooting:
				g_util_webserial.send("system/application", "booting");
				gui_screen_set(gui_screen_animation_startup);
				while(gui_screen_get() == gui_screen_animation_startup) {
					int serial_data = '\n';

					while(serial_data == '\n' && Serial.available() > 1) {
						serial_data = Serial.peek();
						if(serial_data == '\n') {
							Serial.read();
						}
					}
					gui_screen_update(true);
				}
				g_system_runtime.setStatus(StatusOffline);
				break;
			case StatusOffline:
				if(oldStatus == StatusBooting) {
					g_util_webserial.send("system/application", "offline");
					g_system_runtime.set("gui/screen:splash/filename", "error.jpg");
					gui_screen_set(gui_screen_splash);
				}
				if(oldStatus == StatusOnline) {
					g_system_runtime.setStatus(StatusResetting);
				}
				break;
			case StatusOnline:
				g_util_webserial.send("system/application", "online");
				gui_screen_set(gui_screen_idle);
				break;
			case StatusResetting:
				g_util_webserial.send("system/application", "resetting");
				system_reset();
				break;
			case StatusRebooting:
				g_util_webserial.send("system/application", "rebooting");
				gui_screen_set(gui_screen_animation_shutdown);
				while(gui_screen_get() == gui_screen_animation_shutdown) {
					gui_screen_update(true);
				}
				system_reset();
				break;
			case StatusHalting:
				g_util_webserial.send("system/application", "halting");
				gui_screen_set(gui_screen_animation_shutdown);
				while(gui_screen_get() == gui_screen_animation_shutdown) {
					gui_screen_update(true);
				}
				system_halt();
				break;
			default:
				g_util_webserial.send("syslog/error", "invalid runtime status => resetting");
				system_reset();
		}
		oldStatus = newStatus;
	}
	gui_screen_update(false);
}

