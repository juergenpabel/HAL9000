#include "gui/overlay/overlay.h"
#include "globals.h"

static gui_overlay_func  g_overlay = gui_overlay_none;
static bool              g_overlay_forced_refresh = false;


gui_overlay_func gui_overlay_get() {
	return g_overlay;
}


gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func) {
	static etl::string<GLOBAL_VALUE_SIZE> payload;
	       gui_overlay_func               previous_overlay = nullptr;

	if(overlay_func != nullptr && overlay_func != g_overlay) {
		previous_overlay = g_overlay;
		g_overlay = overlay_func;
		gui_overlay_set_refresh();
		if(overlay_name.size() > 0) {
			payload = "{\"overlay\":\"<NAME>\"}";
			payload.replace(12, 6, overlay_name);
			g_util_webserial.send("gui/event", payload, false);
		}
	}
	return previous_overlay;
}


void gui_overlay_set_refresh() {
	g_overlay_forced_refresh = true;
}


bool gui_overlay_update(bool refresh) {
	if(g_overlay_forced_refresh == true) {
		g_overlay_forced_refresh = false;
		refresh = true;
	}
	if(refresh == true) {
		if(g_gui_overlay.getPointer() != nullptr) {
			g_gui_overlay.setBitmapColor(TFT_WHITE, TFT_BLACK);
			g_gui_overlay.fillSprite(TFT_BLACK);
		 }
	}
	return g_overlay(refresh);
}


bool gui_overlay_none(bool refresh) {
	return refresh;
}

