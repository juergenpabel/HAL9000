#include <TimeLib.h>

#include "gui/screen/screen.h"
#include "gui/screen/animations/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/menu/screen.h"
#include "gui/screen/qrcode/screen.h"
#include "gui/screen/splash/screen.h"
#include "gui/overlay/overlay.h"
#include "application/environment.h"
#include "globals.h"


void on_gui_screen(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& body) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;
	static gui_screen_name screen_name;
	       gui_screen_func screen_func = nullptr;

	if(body.containsKey("off") == true) {
		screen_name = "off";
		screen_func = gui_screen_off;
	}
	if(body.containsKey("on") == true) {
		screen_name = "on";
		screen_func = gui_screen_on;
	}
	if(body.containsKey("animations") == true) {
		g_application.delEnv("gui/screen:animations/name");
		if(body["animations"].containsKey("name") == true) {
			g_application.setEnv("gui/screen:animations/name", body["animations"]["name"].as<const char*>());
		}
		screen_name = "animations";
		screen_func = gui_screen_animations;
	}
	if(body.containsKey("error") == true) {
		g_application.delEnv("gui/screen:error/message");
		g_application.delEnv("gui/screen:error/url");
		g_application.delEnv("gui/screen:error/id");
		if(body["error"].containsKey("id") == true) {
			g_application.setEnv("gui/screen:error/id", body["error"]["id"].as<const char*>());
		}
		if(body["error"].containsKey("message") == true) {
			g_application.setEnv("gui/screen:error/message", body["error"]["message"].as<const char*>());
		}
		if(body["error"].containsKey("url") == true) {
			g_application.setEnv("gui/screen:error/url", body["error"]["url"].as<const char*>());
		}
		screen_name = "error";
		screen_func = gui_screen_error;
	}
	if(body.containsKey("idle") == true) {
		screen_name = "idle";
		screen_func = gui_screen_idle;
	}
	if(body.containsKey("menu") == true) {
		g_application.delEnv("gui/screen:menu/title");
		g_application.delEnv("gui/screen:menu/text");
		if(body["menu"].containsKey("title") == true) {
			g_application.setEnv("gui/screen:menu/title", body["menu"]["title"].as<const char*>());
		}
		if(body["menu"].containsKey("text") == true) {
			g_application.setEnv("gui/screen:menu/text",  body["menu"]["text"].as<const char*>());
		}
		screen_name = "menu";
		screen_func = gui_screen_menu;
	}
	if(body.containsKey("none") == true) {
		screen_name = "none";
		screen_func = gui_screen_none;
	}
	if(body.containsKey("qrcode") == true) {
		g_application.delEnv("gui/screen:qrcode/textsize-above");
		g_application.delEnv("gui/screen:qrcode/text-above");
		g_application.delEnv("gui/screen:qrcode/text-url");
		g_application.delEnv("gui/screen:qrcode/text-below");
		g_application.delEnv("gui/screen:qrcode/textsize-below");
		if(body["qrcode"].containsKey("title") == true) {
			g_application.setEnv("gui/screen:qrcode/text-above", body["qrcode"]["title"].as<const char*>());
			g_application.setEnv("gui/screen:qrcode/textsize-above", "normal");
		}
		if(body["qrcode"].containsKey("url") == true) {
			g_application.setEnv("gui/screen:qrcode/text-url", body["qrcode"]["url"].as<const char*>());
		}
		if(body["qrcode"].containsKey("hint") == true) {
			g_application.setEnv("gui/screen:qrcode/text-below", body["qrcode"]["hint"].as<const char*>());
			g_application.setEnv("gui/screen:qrcode/textsize-below", "small");
		}
		screen_name = "qrcode";
		screen_func = gui_screen_qrcode;
	}
	if(body.containsKey("splash") == true) {
		g_application.delEnv("gui/screen:splash/message");
		g_application.delEnv("gui/screen:splash/url");
		g_application.delEnv("gui/screen:splash/id");
		if(body["splash"].containsKey("message") == true) {
			g_application.setEnv("gui/screen:splash/message", body["splash"]["message"].as<const char*>());
		}
		if(body["splash"].containsKey("url") == true) {
			g_application.setEnv("gui/screen:splash/url", body["splash"]["url"].as<const char*>());
		}
		if(body["splash"].containsKey("id") == true) {
			g_application.setEnv("gui/screen:splash/id", body["splash"]["id"].as<const char*>());
		}
		screen_name = "splash";
		screen_func = gui_screen_splash;
	}
	if(screen_func != nullptr) {
		gui_screen_set(screen_name, screen_func);
		response.clear();
		response["screen"] = screen_name.c_str();
		g_util_webserial.send("gui/screen", response);
	} else {
		g_util_webserial.send("syslog/error", body);
	}
}


void on_gui_overlay(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& body) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;
	static gui_overlay_name overlay_name;
	       gui_overlay_func overlay_func = nullptr;

	if(body.containsKey("none") == true) {
		overlay_name = "none";
		overlay_func = gui_overlay_none;
	}
	if(body.containsKey("volume") == true) {
		if(body["volume"].containsKey("level") == true) {
			g_application.setEnv("gui/overlay:volume/level", body["volume"]["level"].as<const char*>());
		}
		if(body["volume"].containsKey("mute") == true) {
			g_application.setEnv("gui/overlay:volume/mute", body["volume"]["mute"].as<const char*>());
		}
		overlay_name = "volume";
		overlay_func = gui_overlay_volume;
	}
	if(body.containsKey("message") == true) {
		if(body["message"].containsKey("text") == true) {
			g_application.setEnv("gui/overlay:message/text", body["message"]["text"].as<const char*>());
		}
		overlay_name = "message";
		overlay_func = gui_overlay_message;
	}
	if(overlay_func != nullptr) {
		gui_overlay_set(overlay_name, overlay_func);
		response.clear();
		response["overlay"] = overlay_name.c_str();
		g_util_webserial.send("gui/overlay", response);
	} else {
		g_util_webserial.send("syslog/error", body);
	}
}

