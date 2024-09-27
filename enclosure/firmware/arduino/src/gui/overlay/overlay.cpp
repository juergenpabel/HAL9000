#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"

static gui_overlay_name  g_overlay_name = "none";
static gui_overlay_func  g_overlay = gui_overlay_none;
static bool              g_overlay_refresh = false;


const gui_overlay_name& gui_overlay_getname() {
	return g_overlay_name;
}


gui_overlay_func gui_overlay_get() {
	return g_overlay;
}


gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func) {
	gui_overlay_func previous_overlay_func = nullptr;

	if(overlay_func != nullptr) {
		previous_overlay_func = g_overlay;
		g_overlay = overlay_func;
		g_overlay_name = overlay_name;
		gui_screen_set_refresh();
		gui_overlay_set_refresh();
	}
	return previous_overlay_func;
}


void gui_overlay_set_refresh() {
	g_overlay_refresh = true;
}


unsigned long gui_overlay_update(unsigned long validity, TFT_eSPI* gui) {
	if(g_overlay_refresh == true) {
		validity = GUI_INVALIDATED;
		g_overlay_refresh = false;
	}
	return g_overlay(validity, gui);
}


unsigned long gui_overlay_off(unsigned long validity, TFT_eSPI* gui) {
	return validity;
}


unsigned long gui_overlay_on(unsigned long validity, TFT_eSPI* gui) {
	return validity;
}


unsigned long gui_overlay_none(unsigned long validity, TFT_eSPI* gui) {
	return GUI_INVALIDATED;
}

