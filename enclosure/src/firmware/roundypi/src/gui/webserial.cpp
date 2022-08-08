#include <string.h>
#include <TimeLib.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "gui/screen/sequence/sequence.h"
#include "gui/screen/sequence/frame.h"
#include "gui/screen/splash/splash.h"
#include "gui/screen/splash/jpeg.h"
#include "gui/screen/splash/png.h"
#include "globals.h"


void on_gui_screen(JSONVar parameter) {
	char     filename[256] = {0};
	char*    extension = NULL;

	if(parameter.hasOwnProperty("splash")) {
		if(parameter["splash"].hasOwnProperty("filename")) {
			g_splash_timeout = 0;
			if(parameter["splash"].hasOwnProperty("timeout")) {
				g_splash_timeout = (long)parameter["splash"]["timeout"] + now();
			}
			snprintf(filename, sizeof(filename)-1, "/images/splash/%s", (const char*)parameter["splash"]["filename"]);
			extension = strrchr(filename, '.');
			if(extension != NULL && strncmp(extension, ".jpg", 5) == 0) {
				splash_jpeg(filename);
			}
			if(extension != NULL && strncmp(extension, ".png", 5) == 0) {
				splash_png(filename);
			}
			g_previous_screen = screen_update(screen_update_splash, false);
		}
	}
	if(parameter.hasOwnProperty("sequence")) {
		if(parameter["sequence"].hasOwnProperty("queue")) {
			sequence_add(parameter["sequence"]["queue"]);
			screen_update(screen_update_sequence, false);
		}
	}
}


void on_gui_overlay(JSONVar parameter) {
	if(parameter.hasOwnProperty("show")) {
		if(String("volume").equals(parameter["show"])) {
			overlay_update(overlay_update_volume);
		}
		if(String("message").equals(parameter["show"])) {
			overlay_update(overlay_update_message);
		}
	}
	if(parameter.hasOwnProperty("hide")) {
		overlay_update(overlay_update_none);
	}
}

