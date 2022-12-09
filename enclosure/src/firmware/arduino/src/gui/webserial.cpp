#include <TimeLib.h>

#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/menu/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/animations/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void on_gui_screen(const JsonVariant& body) {
	gui_screen_func screen = gui_screen_none;

	if(body.containsKey("idle")) {
		if(body["idle"].containsKey("clock")) {
			g_system_runtime["gui/screen:idle/clock"] = body["idle"]["clock"].as<const char*>();
		}
		screen = gui_screen_idle;
	}
	if(body.containsKey("menu")) {
		if(body["menu"].containsKey("title")) {
			g_system_runtime["gui/screen:menu/title"] = body["menu"]["title"].as<const char*>();
		}
		if(body["menu"].containsKey("text")) {
			g_system_runtime["gui/screen:menu/text"]  = body["menu"]["text"].as<const char*>();
		}
		screen = gui_screen_menu;
	}
	if(body.containsKey("splash")) {
		if(body["splash"].containsKey("filename")) {
			etl::string<GLOBAL_FILENAME_SIZE> filename = body["splash"]["filename"].as<const char*>();

			if(filename.substr(filename.size()-4,4).compare(".jpg") != 0) {
				g_util_webserial.send("syslog/warn", "on_gui_screen() => 'splash' screen called with non-jpeg filename (*.jpg)");
				g_util_webserial.send("syslog/warn", filename);
				return;
			}
			g_system_runtime["gui/screen:splash/filename"] = filename;
		}
		screen = gui_screen_splash;
	}
	if(body.containsKey("hal9000")) {
		if((body["hal9000"].containsKey("queue")) && (body["hal9000"].containsKey("sequence"))) {
			static StaticJsonDocument<1024> queue;
			       int                      queue_pos = -1;

			queue.clear();
			if(g_system_runtime.exists("gui/screen:hal9000/queue") == true) {
				if(g_system_runtime["gui/screen:hal9000/queue"].size() > 0) {
					deserializeJson(queue, g_system_runtime["gui/screen:hal9000/queue"]);
				}
			}
			if((body["hal9000"]["sequence"].containsKey("name")) && (body["hal9000"]["sequence"].containsKey("loop"))) {
				if(strncmp(body["hal9000"]["queue"].as<const char*>(), "replace", 8) == 0) {
					queue.clear();
					deserializeJson(queue, "[]");
					queue_pos = 0;
				}
				if(strncmp(body["hal9000"]["queue"].as<const char*>(), "append", 7) == 0) {
					queue_pos = queue.size();
				}
			}
			if(queue_pos >= 0) {
				queue[queue_pos] = JsonArray();
				queue[queue_pos]["name"] = body["hal9000"]["sequence"]["name"];
				queue[queue_pos]["loop"] = body["hal9000"]["sequence"]["loop"];
				RuntimeWriter runtimewriter(g_system_runtime, "gui/screen:hal9000/queue");
				serializeJson(queue, runtimewriter);
				screen = gui_screen_hal9000;
			}
		}
	}
	if(screen != gui_screen_none) {
		gui_screen_set(screen);
	}
}


void on_gui_overlay(const JsonVariant& body) {
	gui_overlay_func overlay = gui_overlay_none;

	if(body.containsKey("volume")) {
		if(body["volume"].containsKey("level")) {
			g_system_runtime["gui/overlay:volume/level"] = body["volume"]["level"].as<const char*>();
		}
		if(body["volume"].containsKey("mute")) {
			g_system_runtime["gui/overlay:volume/mute"] = body["volume"]["mute"].as<const char*>();
		}
		overlay = gui_overlay_volume;
	}
	if(body.containsKey("message")) {
		if(body["message"].containsKey("text")) {
			g_system_runtime["gui/overlay:message/text"] = body["message"]["text"].as<const char*>();
		}
		overlay = gui_overlay_message;
	}
	gui_overlay_set(overlay);
}

