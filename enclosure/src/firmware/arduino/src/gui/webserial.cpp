#include <TimeLib.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/screen/menu/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/hal9000/sequence.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void on_gui_screen(JSONVar parameter) {

	if(parameter.hasOwnProperty("screen")) {
		if(parameter["screen"].hasOwnProperty("idle")) {
			if(arduino::String("show") == parameter["screen"]["idle"]) {
				gui_screen_set(gui_screen_idle);
			}
		}
		if(parameter["screen"].hasOwnProperty("menu")) {
			if(parameter["screen"].hasOwnProperty("data")) {
				g_system_runtime["gui/screen:menu/title"] = (const char*)parameter["screen"]["data"]["title"];
				g_system_runtime["gui/screen:menu/text"] = (const char*)parameter["screen"]["data"]["text"];
			}
			if(arduino::String("show") == parameter["screen"]["menu"]) {
				gui_screen_set(gui_screen_menu);
			}
		}
		if(parameter["screen"].hasOwnProperty("hal9000")) {
			if(arduino::String("show") == parameter["screen"]["hal9000"]) {
				if(parameter["screen"]["data"].hasOwnProperty("frames")) {
					if(gui_screen_set(gui_screen_hal9000) != gui_screen_hal9000) {
						gui_screen_hal9000_frames_load(parameter["screen"]["data"]["frames"]);
					}
				}
			}
		}
		if(parameter["screen"].hasOwnProperty("splash")) {
			if(arduino::String("show") == parameter["screen"]["splash"]) {
				if(parameter["screen"]["data"].hasOwnProperty("filename")) {
					std::string filename = (const char*)parameter["screen"]["data"]["filename"];

					if(filename.substr(filename.length()-4,4).compare(".jpg") != 0) {
						g_util_webserial.send("syslog", "on_gui_screen() => 'splash' screen called with non-jpeg filename (*.jpg)");
						g_util_webserial.send("syslog", filename.c_str());
						return;
					}
					g_system_runtime["gui/screen:splash/filename"] = filename;
					gui_screen_set(gui_screen_splash);
				}
			}
		}
		if(parameter["screen"].hasOwnProperty("sequence")) {
			if(arduino::String("show") == parameter["screen"]["sequence"]) {
				if(parameter["screen"]["data"].hasOwnProperty("queue")) {
					sequence_add(parameter["screen"]["data"]["queue"]);
					gui_screen_set(gui_screen_sequence);
				}
			}
		}
	}
}


void on_gui_overlay(JSONVar parameter) {
	if(parameter.hasOwnProperty("overlay")) {
		if(parameter["overlay"].hasOwnProperty("volume")) {
			if(parameter["overlay"].hasOwnProperty("data")) {
				if(parameter["overlay"]["data"].hasOwnProperty("level")) {
					g_system_runtime["gui/screen:volume/level"] = (const char*)parameter["overlay"]["data"]["level"];
				}
				if(parameter["overlay"]["data"].hasOwnProperty("mute")) {
					g_system_runtime["gui/screen:volume/mute"] = (const char*)parameter["overlay"]["data"]["mute"];
				}
			}
			if(arduino::String("show") == parameter["overlay"]["volume"]) {
				gui_overlay_set(gui_overlay_volume);
			}
			if(arduino::String("hide") == parameter["overlay"]["volume"]) {
				gui_overlay_set(gui_overlay_none);
			}
		}
		if(parameter["overlay"].hasOwnProperty("message")) {
			if(parameter["overlay"].hasOwnProperty("data")) {
				g_system_runtime["gui/overlay:message/text"] = (const char*)parameter["overlay"]["data"]["text"];
			}
			if(arduino::String("show") == parameter["overlay"]["message"]) {
				gui_overlay_set(gui_overlay_message);
			}
			if(arduino::String("hide") == parameter["overlay"]["message"]) {
				gui_overlay_set(gui_overlay_none);
			}
		}
	}
}

