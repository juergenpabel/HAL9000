#include <etl/string.h>
#include <etl/to_string.h>
#include <TimeLib.h>

#include "gui/screen/screen.h"
#include "gui/screen/animations/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/menu/screen.h"
#include "gui/screen/qrcode/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/overlay/overlay.h"
#include "system/environment.h"
#include "globals.h"


void on_gui_screen(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& body) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;
	static etl::string<GLOBAL_KEY_SIZE> screen_name;
	static etl::string<GLOBAL_KEY_SIZE> screen_data;
	       gui_screen_func screen_func = nullptr;

	response.clear();
	screen_name.clear();
	screen_data.clear();
	if(body.isNull() == true || body.is<const char*>() == true) {
		response["screen"] = gui_screen_getname();
		g_util_webserial.send("gui/screen", response);
		return;
	}
	if(body.containsKey("off") == true) {
		gui_screen_set("off", gui_screen_off);
		return;
	}
	if(body.containsKey("on") == true) {
		gui_screen_set("on", gui_screen_on);
		return;
	}
	if(body.containsKey("animations") == true) {
		g_system_application.delEnv("gui/screen:animations/name");
		if(body["animations"].containsKey("name") == true) {
			g_system_application.setEnv("gui/screen:animations/name", body["animations"]["name"].as<const char*>());
			screen_name = "animations";
			screen_data = g_system_application.getEnv("gui/screen:animations/name");
			screen_func = gui_screen_animations;
		}
	}
	if(body.containsKey("error") == true) {
		g_system_application.delEnv("gui/screen:error/id");
		g_system_application.delEnv("gui/screen:error/title");
		g_system_application.delEnv("gui/screen:error/url");
		if(body["error"].containsKey("id") == true) {
			g_system_application.setEnv("gui/screen:error/id", body["error"]["id"].as<const char*>());
		}
		if(body["error"].containsKey("title") == true) {
			g_system_application.setEnv("gui/screen:error/title", body["error"]["title"].as<const char*>());
		}
		if(body["error"].containsKey("url") == true) {
			g_system_application.setEnv("gui/screen:error/url", body["error"]["url"].as<const char*>());
		}
		screen_name = "error";
		screen_data = g_system_application.getEnv("gui/screen:error/id");
		screen_func = gui_screen_error;
	}
	if(body.containsKey("idle") == true) {
		screen_name = "idle";
		screen_func = gui_screen_idle;
	}
	if(body.containsKey("menu") == true) {
		g_system_application.delEnv("gui/screen:menu/title");
		g_system_application.delEnv("gui/screen:menu/text");
		if(body["menu"].containsKey("title") == true) {
			g_system_application.setEnv("gui/screen:menu/title", body["menu"]["title"].as<const char*>());
		}
		if(body["menu"].containsKey("text") == true) {
			g_system_application.setEnv("gui/screen:menu/text",  body["menu"]["text"].as<const char*>());
		}
		screen_name = "menu";
		screen_data = body["menu"].containsKey("name") ? body["menu"]["name"].as<const char*>() : "unknown/unknown";
		screen_func = gui_screen_menu;
	}
	if(body.containsKey("none") == true) {
		screen_name = "none";
		screen_func = gui_screen_none;
	}
	if(body.containsKey("qrcode") == true) {
		g_system_application.delEnv("gui/screen:qrcode/textsize-above");
		g_system_application.delEnv("gui/screen:qrcode/text-above");
		g_system_application.delEnv("gui/screen:qrcode/text-url");
		g_system_application.delEnv("gui/screen:qrcode/text-below");
		g_system_application.delEnv("gui/screen:qrcode/textsize-below");
		if(body["qrcode"].containsKey("title") == true) {
			g_system_application.setEnv("gui/screen:qrcode/text-above", body["qrcode"]["title"].as<const char*>());
			g_system_application.setEnv("gui/screen:qrcode/textsize-above", "normal");
		}
		if(body["qrcode"].containsKey("url") == true) {
			g_system_application.setEnv("gui/screen:qrcode/text-url", body["qrcode"]["url"].as<const char*>());
		}
		if(body["qrcode"].containsKey("hint") == true) {
			g_system_application.setEnv("gui/screen:qrcode/text-below", body["qrcode"]["hint"].as<const char*>());
			g_system_application.setEnv("gui/screen:qrcode/textsize-below", "small");
		}
		screen_name = "qrcode";
		screen_func = gui_screen_qrcode;
	}
	if(body.containsKey("splash") == true) {
		g_system_application.delEnv("gui/screen:splash/message");
		g_system_application.delEnv("gui/screen:splash/url");
		g_system_application.delEnv("gui/screen:splash/id");
		if(body["splash"].containsKey("message") == true) {
			g_system_application.setEnv("gui/screen:splash/message", body["splash"]["message"].as<const char*>());
		}
		if(body["splash"].containsKey("url") == true) {
			g_system_application.setEnv("gui/screen:splash/url", body["splash"]["url"].as<const char*>());
		}
		if(body["splash"].containsKey("id") == true) {
			g_system_application.setEnv("gui/screen:splash/id", body["splash"]["id"].as<const char*>());
		}
		screen_name = "splash";
		screen_data = g_system_application.getEnv("gui/screen:splash/id");
		screen_func = gui_screen_splash;
	}
	if(screen_func != nullptr) {
		if(screen_data.empty() == false) {
			screen_name += ":";
			screen_name += screen_data;
		}
		if(gui_screen_set(screen_name, screen_func) != nullptr) {
			response["result"] = "OK";
			response["screen"] = screen_name;
			g_util_webserial.send("gui/screen", response);
		}
	} else {
		g_util_webserial.send("syslog/warn", body);
	}
}


void on_gui_overlay(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& body) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;
	static etl::string<GLOBAL_KEY_SIZE> overlay_name;
	static etl::string<GLOBAL_KEY_SIZE> overlay_data;
	       gui_overlay_func overlay_func = nullptr;

	response.clear();
	overlay_name.clear();
	overlay_data.clear();
	if(body.isNull() == true || body.is<const char*>() == true) {
		response["overlay"] = gui_overlay_getname();
		g_util_webserial.send("gui/overlay", response);
		return;
	}
	if(body.containsKey("none") == true) {
		overlay_name = "none";
		overlay_func = gui_overlay_none;
	}
	if(body.containsKey("volume") == true) {
		if(body["volume"].containsKey("level") == true) {
			if(body["volume"]["level"].is<unsigned char>() == true) {
				unsigned char volume;

				volume = body["volume"]["level"].as<unsigned char>();
				if(volume >= 0 && volume <= 100) {
					etl::string<4> volume_string;

					etl::to_string(volume, volume_string);
					g_system_application.setEnv("gui/overlay:volume/level", volume_string);
					overlay_name = "volume";
					overlay_data = volume_string;
					overlay_func = gui_overlay_volume;
				}
			}
		}
		if(body["volume"].containsKey("mute") == true) {
			if(body["volume"]["mute"].is<bool>() == true) {
				switch(body["volume"]["mute"].as<bool>()) {
					case true:
						g_system_application.setEnv("gui/overlay:volume/mute", "true");
						break;
					case false:
						g_system_application.setEnv("gui/overlay:volume/mute", "false");
						break;
				}
				overlay_name = "volume";
				overlay_data = body["volume"]["mute"].as<bool>() ? "mute" : g_system_application.getEnv("gui/overlay:volume/level");
				overlay_func = gui_overlay_volume;
			}
		}
	}
	if(body.containsKey("message") == true) {
		if(body["message"].containsKey("text") == true) {
			g_system_application.setEnv("gui/overlay:message/text", body["message"]["text"].as<const char*>());
		}
		if(body["message"].containsKey("position-vertical") == true) {
			g_system_application.setEnv("gui/overlay:message/position-vertical", body["message"]["position-vertical"].as<const char*>());
		}
		overlay_name = "message";
		overlay_func = gui_overlay_message;
	}
	if(overlay_func != nullptr) {
		gui_overlay_set(overlay_name, overlay_func);
		response["result"] = "OK";
		response["overlay"] = overlay_name;
		g_util_webserial.send("gui/overlay", response);
	} else {
		g_util_webserial.send("syslog/warn", body);
	}
}

