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
	gui_screen_func screen = nullptr;

	if(body.containsKey("animations") == true) {
		g_application.delEnv("gui/screen:animations/name");
		if(body["animations"].containsKey("name") == true) {
			g_application.setEnv("gui/screen:animations/name", body["animations"]["name"].as<const char*>());
		}
		screen = gui_screen_animations;
		g_util_webserial.send("syslog/debug", "gui/screen:animations => OK");
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
		g_util_webserial.send("syslog/debug", "gui/screen:error => OK");
		screen = gui_screen_error;
	}
	if(body.containsKey("idle") == true) {
		screen = gui_screen_idle;
		g_util_webserial.send("syslog/debug", "gui/screen:idle => OK");
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
		screen = gui_screen_menu;
		g_util_webserial.send("syslog/debug", "gui/screen:menu => OK");
	}
	if(body.containsKey("none") == true) {
		screen = gui_screen_none;
		g_util_webserial.send("syslog/debug", "gui/screen:none => OK");
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
		screen = gui_screen_qrcode;
		g_util_webserial.send("syslog/debug", "gui/screen:qrcode => OK");
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
		screen = gui_screen_splash;
		g_util_webserial.send("syslog/debug", "gui/screen:splash => OK");
	}
	if(screen != nullptr) {
		gui_screen_set(screen);
	}
}


void on_gui_overlay(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& body) {
	gui_overlay_func overlay = nullptr;

	if(body.containsKey("none") == true) {
		overlay = gui_overlay_none;
		g_util_webserial.send("syslog/debug", "gui/overlay:none => OK");
	}
	if(body.containsKey("volume") == true) {
		if(body["volume"].containsKey("level") == true) {
			g_application.setEnv("gui/overlay:volume/level", body["volume"]["level"].as<const char*>());
		}
		if(body["volume"].containsKey("mute") == true) {
			g_application.setEnv("gui/overlay:volume/mute", body["volume"]["mute"].as<const char*>());
		}
		overlay = gui_overlay_volume;
		g_util_webserial.send("syslog/debug", "gui/overlay:volume => OK");
	}
	if(body.containsKey("message") == true) {
		if(body["message"].containsKey("text") == true) {
			g_application.setEnv("gui/overlay:message/text", body["message"]["text"].as<const char*>());
		}
		overlay = gui_overlay_message;
		g_util_webserial.send("syslog/debug", "gui/overlay:message => OK");
	}
	if(overlay != nullptr) {
		gui_overlay_set(overlay);
	}
}

