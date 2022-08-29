#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


static screen_func  g_screen = screen_idle;
static bool         g_screen_forced_refresh = false;


screen_func screen_get() {
	return g_screen;
}


screen_func screen_set(screen_func new_screen) {
	screen_func previous_screen;

	previous_screen = g_screen;
	if(new_screen != NULL) {
		g_screen = new_screen;
		g_screen_forced_refresh = true;
		if(previous_screen != new_screen && new_screen == screen_idle) {
			g_gui_screen_idle_clock_previously = 0;
		}
	}
	return previous_screen;
}


void screen_set_refresh() {
	g_screen_forced_refresh = true;
}


void screen_update(bool force_refresh) {
	if(force_refresh == false) {
		force_refresh = g_screen_forced_refresh;
		g_screen_forced_refresh = false;
	}
	overlay_update(force_refresh);
	g_screen(force_refresh);
	g_gui_tft_overlay.pushSprite(0, 0, TFT_BLACK);
}

