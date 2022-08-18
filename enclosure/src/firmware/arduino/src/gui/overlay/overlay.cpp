#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"

static overlay_func  g_overlay = overlay_none;


overlay_func overlay_get() {
	return g_overlay;
}


overlay_func overlay_set(overlay_func new_overlay) {
	overlay_func previous_overlay = NULL;
	if(new_overlay != NULL) {
		if(new_overlay != g_overlay) {
			previous_overlay = g_overlay;
			g_overlay = new_overlay;
			screen_set_refresh();
		}
	}
	return previous_overlay;
}


void overlay_update(bool force_refresh) {
	if(force_refresh) {
		g_gui_tft_overlay.fillSprite(TFT_BLACK);
	}
	g_overlay(force_refresh);
}


void overlay_none(bool force_refresh) {
}

