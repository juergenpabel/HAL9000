#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


static gui_screen_func  g_gui_screen = gui_screen_idle;
static bool             g_gui_screen_forced_refresh = false;


gui_screen_func gui_screen_get() {
	return g_gui_screen;
}


gui_screen_func gui_screen_set(gui_screen_func new_screen) {
	gui_screen_func previous_screen;

	previous_screen = g_gui_screen;
	if(new_screen != nullptr) {
		g_gui_screen = new_screen;
		g_gui_screen_forced_refresh = true;
	}
	return previous_screen;
}


void gui_screen_set_refresh() {
	g_gui_screen_forced_refresh = true;
}


void gui_screen_update(bool refresh) {
	if(refresh == false) {
		refresh = g_gui_screen_forced_refresh;
		g_gui_screen_forced_refresh = false;
	}
	gui_overlay_update(refresh);
	g_gui_screen(refresh);
	g_device_tft_overlay.pushSprite(0, 0, TFT_BLACK);
}


void gui_screen_none(bool refresh) {
	(void)refresh;
}

