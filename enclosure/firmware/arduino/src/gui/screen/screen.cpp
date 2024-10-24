#include "gui/screen/screen.h"
#include "gui/screen/animations/screen.h"
#include "globals.h"


static gui_screen_func  g_screen_func = gui_screen_none;
static gui_screen_name  g_screen_name = "none";
static bool             g_screen_refresh = false;


const gui_screen_name& gui_screen_getname() {
	return g_screen_name;
}


gui_screen_func gui_screen_get() {
	return g_screen_func;
}


gui_screen_func gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> webserial_event;
	       bool                                    webserial_event_delayed = false;
	       gui_screen_func                         previous_screen_func = nullptr;

	if(screen_func != nullptr) {
		previous_screen_func = g_screen_func;
		g_screen_name = screen_name;
		g_screen_func = screen_func;
		gui_screen_set_refresh();
		if(screen_func == gui_screen_animations) {
			if(previous_screen_func != gui_screen_animations) {
				gui_screen_animations(GUI_RELOAD, nullptr); // clear out any remaining animations from queue
			} else {
				webserial_event_delayed = true;
			}
		}
		if(webserial_event_delayed == false) {
			webserial_event.clear();
			webserial_event["screen"] = screen_name;
			g_util_webserial.send("gui/screen", webserial_event);
		}
	}
	return previous_screen_func;
}


void gui_screen_set_refresh() {
	g_screen_refresh = true;
}


unsigned long gui_screen_update(unsigned long validity, TFT_eSPI* gui) {
	if(g_screen_refresh == true) {
		g_screen_refresh = false;
		validity = GUI_INVALIDATED;
	}
	return g_screen_func(validity, gui);
}


unsigned long gui_screen_none(unsigned long validity, TFT_eSPI* gui) {
	if(validity == GUI_INVALIDATED) {
		gui->fillScreen(TFT_BLACK);
		validity = millis();
	}
	return validity;
}

