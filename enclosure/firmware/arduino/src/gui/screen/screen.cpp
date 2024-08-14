#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


static gui_screen_func  g_screen = gui_screen_on;
static bool             g_screen_refresh = false;


gui_screen_func gui_screen_get() {
	return g_screen;
}


gui_screen_func gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func, bool screen_refresh) {
	static etl::string<GLOBAL_VALUE_SIZE> payload;
	       gui_screen_func                previous_screen = nullptr;

	if(screen_func != nullptr && screen_func != g_screen) {
		previous_screen = g_screen;
		g_screen = screen_func;
		g_screen_refresh = screen_refresh;
		if(screen_refresh == true) {
                        if(g_gui_screen.getPointer() != nullptr) {
                                g_gui_screen.fillSprite(TFT_TRANSPARENT);
                        }
			gui_overlay_set_refresh();
		}
	}
	return previous_screen;
}


void gui_screen_set_refresh() {
	g_screen_refresh = true;
}


gui_refresh_t gui_screen_update(bool refresh) {
	if(g_screen_refresh == true) {
		g_screen_refresh = false;
		refresh = true;
	}
	return g_screen(refresh);
}


gui_refresh_t gui_screen_off(bool refresh) {
	if(refresh == true) {
		gui_overlay_set("off", gui_overlay_off, false);
		g_device_board.displayOff();
	}
	return RefreshIgnore;
}


gui_refresh_t gui_screen_on(bool refresh) {
	if(refresh == true) {
		g_device_board.displayOn();
		gui_overlay_set("on", gui_overlay_on, false);
	}
	return RefreshAll;
}


gui_refresh_t gui_screen_none(bool refresh) {
	if(refresh == true) {
		return RefreshScreen;
	}
	return RefreshIgnore;
}

