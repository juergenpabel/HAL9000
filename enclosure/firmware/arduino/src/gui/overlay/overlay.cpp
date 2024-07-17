#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"

static gui_overlay_func  g_overlay = gui_overlay_none;


gui_overlay_func gui_overlay_get() {
	return g_overlay;
}


gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func) {
	static etl::string<GLOBAL_VALUE_SIZE> payload;
	       gui_overlay_func               previous_overlay = nullptr;

	if(overlay_func != nullptr && overlay_func != g_overlay) {
		previous_overlay = g_overlay;
		g_overlay = overlay_func;
		gui_screen_set_refresh();
		if(overlay_name.size() > 0) {
			payload = "{\"overlay\":\"<NAME>\"}";
			payload.replace(12, 6, overlay_name);
			g_util_webserial.send("gui/event", payload, false);
		}
	}
	return previous_overlay;
}


void gui_overlay_update(bool refresh) {
	if(refresh) {
		g_gui_overlay.setBitmapColor(TFT_WHITE, TFT_BLACK);
		g_gui_overlay.fillSprite(TFT_BLACK);
	}
	g_overlay(refresh);
}


void gui_overlay_none(bool refresh) {
}

