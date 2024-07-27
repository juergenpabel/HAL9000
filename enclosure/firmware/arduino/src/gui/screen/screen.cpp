#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


static gui_screen_func  g_screen = gui_screen_none;
static bool             g_screen_forced_refresh = false;


gui_screen_func gui_screen_get() {
	return g_screen;
}


void gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func) {
	static etl::string<GLOBAL_VALUE_SIZE> payload;

	if(screen_func != nullptr && screen_func != g_screen) {
		g_screen = screen_func;
		g_screen_forced_refresh = true;
		if(screen_name.size() > 0) {
			payload = "{\"screen\":\"<NAME>\"}";
			payload.replace(11, 6, screen_name);
			g_util_webserial.send("gui/event", payload, false);
		}
	}
}


void gui_screen_set_refresh() {
	g_screen_forced_refresh = true;
}


bool gui_screen_update(bool refresh) {
	if(g_screen_forced_refresh == true) {
		g_screen_forced_refresh = false;
		refresh = true;
	}
	return g_screen(refresh);
}


bool gui_screen_none(bool refresh) {
	return refresh;
}

