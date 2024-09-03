#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"

static gui_overlay_func  g_overlay = gui_overlay_none;
static bool              g_overlay_refresh = false;


gui_overlay_func gui_overlay_get() {
	return g_overlay;
}


gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func) {
	gui_overlay_func previous_overlay_func = nullptr;

	if(overlay_func != nullptr) {
		previous_overlay_func = g_overlay;
		g_overlay = overlay_func;
		gui_screen_set_refresh();
		gui_overlay_set_refresh();
	}
	return previous_overlay_func;
}


void gui_overlay_set_refresh() {
	g_overlay_refresh = true;
}


unsigned long gui_overlay_update(unsigned long lastDraw, TFT_eSPI* gui) {
	if(g_overlay_refresh == true) {
		lastDraw = GUI_UPDATE;
		g_overlay_refresh = false;
	}
	return g_overlay(lastDraw, gui);
}


unsigned long gui_overlay_off(unsigned long lastDraw, TFT_eSPI* gui) {
	return GUI_IGNORE;
}


unsigned long gui_overlay_on(unsigned long lastDraw, TFT_eSPI* gui) {
	return GUI_IGNORE;
}


unsigned long gui_overlay_none(unsigned long lastDraw, TFT_eSPI* gui) {
	return GUI_IGNORE;
}

