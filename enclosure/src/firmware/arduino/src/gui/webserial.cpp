#include <TimeLib.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/menu/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/animations/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void on_gui_screen(JSONVar parameter) {
		if(parameter.hasOwnProperty("idle")) {
			gui_screen_set(gui_screen_idle);
		}
		if(parameter.hasOwnProperty("menu")) {
			if((parameter["menu"].hasOwnProperty("title"))
			&& (parameter["menu"].hasOwnProperty("text"))) {
				g_system_runtime["gui/screen:menu/title"] = (const char*)parameter["menu"]["title"];
				g_system_runtime["gui/screen:menu/text"]  = (const char*)parameter["menu"]["text"];
				gui_screen_set(gui_screen_menu);
			}
		}
		if(parameter.hasOwnProperty("splash")) {
			if(parameter["splash"].hasOwnProperty("filename")) {
				std::string filename = (const char*)parameter["splash"]["filename"];

				if(filename.substr(filename.length()-4,4).compare(".jpg") != 0) {
					g_util_webserial.send("syslog", "on_gui_screen() => 'splash' screen called with non-jpeg filename (*.jpg)");
					g_util_webserial.send("syslog", filename.c_str());
					return;
				}
				g_system_runtime["gui/screen:splash/filename"] = filename;
				gui_screen_set(gui_screen_splash);
			}
		}
		if(parameter.hasOwnProperty("hal9000")) {
			if((parameter["hal9000"].hasOwnProperty("queue"))
			&& (parameter["hal9000"].hasOwnProperty("sequence"))) {
				JSONVar queue = JSONVar::parse("[]");
				int     queue_pos = -1;

				if(g_system_runtime.count("gui/screen:hal9000/queue") == 1) {
					if(g_system_runtime["gui/screen:hal9000/queue"].length() > 0) {
						queue = JSONVar::parse(g_system_runtime["gui/screen:hal9000/queue"].c_str());
					}
				}
				if((parameter["hal9000"]["sequence"].hasOwnProperty("name"))
				&& (parameter["hal9000"]["sequence"].hasOwnProperty("loop"))) {
					if(arduino::String("replace") == parameter["hal9000"]["queue"]) {
						queue = JSONVar::parse("[]");
						queue_pos = 0;
					}
					if(arduino::String("append") == parameter["hal9000"]["queue"]) {
						queue_pos = queue.length();
					}
				}
				if(queue_pos >= 0) {
					queue[queue_pos] = JSONVar();
					queue[queue_pos]["name"] = (const char*)parameter["hal9000"]["sequence"]["name"];
					queue[queue_pos]["loop"] = (const char*)parameter["hal9000"]["sequence"]["loop"];
					g_system_runtime["gui/screen:hal9000/queue"] = JSONVar::stringify(queue).c_str();
					gui_screen_set(gui_screen_hal9000);
				}
			}
		}
		if(parameter.hasOwnProperty("shutdown")) {
			gui_screen_set(gui_screen_animation_shutdown);
		}
}


void on_gui_overlay(JSONVar parameter) {
	if(parameter.hasOwnProperty("overlay")) {
		if(parameter["overlay"].hasOwnProperty("volume")) {
			if(parameter["overlay"].hasOwnProperty("data")) {
				if(parameter["overlay"]["data"].hasOwnProperty("level")) {
					g_system_runtime["gui/overlay:volume/level"] = (const char*)parameter["overlay"]["data"]["level"];
				}
				if(parameter["overlay"]["data"].hasOwnProperty("mute")) {
					g_system_runtime["gui/overlay:volume/mute"] = (const char*)parameter["overlay"]["data"]["mute"];
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

