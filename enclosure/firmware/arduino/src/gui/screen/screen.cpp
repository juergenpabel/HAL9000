#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


static gui_screen_func  g_screen_func = gui_screen_on;
static gui_screen_name  g_screen_name = "on";
static bool             g_screen_refresh = false;


gui_screen_name gui_screen_getname() {
	return g_screen_name;
}


gui_screen_func gui_screen_get() {
	return g_screen_func;
}


gui_screen_func gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func) {
	gui_screen_func previous_screen_func = nullptr;

	if(screen_func != nullptr) {
		previous_screen_func = g_screen_func;
		g_screen_name = screen_name;
		g_screen_func = screen_func;
		gui_screen_set_refresh();
		gui_overlay_set_refresh();
	}
	return previous_screen_func;
}


void gui_screen_set_refresh() {
	g_screen_refresh = true;
}


unsigned long gui_screen_update(unsigned long lastDraw, TFT_eSPI* gui) {
	if(g_screen_refresh == true) {
		g_screen_refresh = false;
		lastDraw = GUI_UPDATE;
	}
	return g_screen_func(lastDraw, gui);
}


unsigned long gui_screen_off(unsigned long lastDraw, TFT_eSPI* gui) {
	if(lastDraw == GUI_UPDATE) {
//TODO		gui_overlay_set("off", gui_overlay_off);
		g_device_board.displayOff();
		return GUI_IGNORE;
	}
	return lastDraw;
}


unsigned long gui_screen_on(unsigned long lastDraw, TFT_eSPI* gui) {
	if(lastDraw == GUI_UPDATE) {
		g_device_board.displayOn();
//TODO		gui_overlay_set("on", gui_overlay_on);
		return GUI_IGNORE;
	}
	return lastDraw;
}


unsigned long gui_screen_none(unsigned long lastDraw, TFT_eSPI* gui) {
	if(lastDraw == GUI_UPDATE) {
		return GUI_IGNORE;
	}
	return lastDraw;
}

