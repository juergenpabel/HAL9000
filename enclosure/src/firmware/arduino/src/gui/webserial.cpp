#include <string.h>
#include <TimeLib.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/hal9000/sequence.h"
#include "gui/screen/splash/screen.h"
#include "gui/screen/splash/jpeg.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void on_gui_screen(JSONVar parameter) {
	char     filename[256] = {0};
	char*    extension = NULL;

	if(parameter.hasOwnProperty("screen")) {
		if(parameter["screen"].hasOwnProperty("idle")) {
			if(String("show").equals(parameter["screen"]["idle"])) {
				screen_set(screen_idle);
			}
		}
		if(parameter["screen"].hasOwnProperty("hal9000")) {
			if(String("show").equals(parameter["screen"]["hal9000"])) {
				if(parameter["screen"]["data"].hasOwnProperty("frames")) {
					if(screen_set(gui_screen_hal9000) != gui_screen_hal9000) {
						gui_screen_hal9000_frames_load(parameter["screen"]["data"]["frames"]);
					}
				}
			}
		}
		if(parameter["screen"].hasOwnProperty("splash")) {
			if(String("show").equals(parameter["screen"]["splash"])) {
				if(parameter["screen"]["data"].hasOwnProperty("filename")) {
					snprintf(filename, sizeof(filename)-1, "/images/splash/%s", (const char*)parameter["screen"]["data"]["filename"]);
					extension = strrchr(filename, '.');
					if(extension == NULL || strncmp(extension, ".jpg", 5) != 0) {
						//TODO:error
						return;
					}
					gui_screen_splash_jpeg(filename);
					screen_set(screen_splash);
				}
			}
		}
		if(parameter["screen"].hasOwnProperty("sequence")) {
			if(String("show").equals(parameter["screen"]["sequence"])) {
				if(parameter["screen"]["data"].hasOwnProperty("queue")) {
					sequence_add(parameter["screen"]["data"]["queue"]);
					screen_set(screen_sequence);
				}
			}
		}
	}
}


void on_gui_overlay(JSONVar parameter) {
	if(parameter.hasOwnProperty("overlay")) {
		if(parameter["overlay"].hasOwnProperty("volume")) {
			if(parameter["overlay"].hasOwnProperty("data")) {
				g_system_settings["audio:volume-level"] = parameter["overlay"]["data"]["level"];
				g_system_settings["audio:volume-mute"] = parameter["overlay"]["data"]["mute"];
			}
			if(String("show").equals(parameter["overlay"]["volume"])) {
				overlay_set(overlay_volume);
			}
			if(String("hide").equals(parameter["overlay"]["volume"])) {
				overlay_set(overlay_none);
			}
		}
		if(parameter["overlay"].hasOwnProperty("message")) {
			if(parameter["overlay"].hasOwnProperty("data")) {
				g_system_settings["overlay:message:text"] = parameter["overlay"]["data"]["text"];
			}
			if(String("show").equals(parameter["overlay"]["message"])) {
				overlay_set(overlay_message);
			}
			if(String("hide").equals(parameter["overlay"]["message"])) {
				overlay_set(overlay_none);
			}
		}
	}
}

