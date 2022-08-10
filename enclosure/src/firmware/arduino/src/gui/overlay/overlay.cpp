#include "globals.h"

#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"


static overlay_update_func g_current_update_func = overlay_update_none;

overlay_update_func overlay_update(overlay_update_func new_update_func) {
	overlay_update_func previous_update_func = NULL;

	if(new_update_func != NULL) {
		previous_update_func = g_current_update_func;
		g_current_update_func = new_update_func;
		screen_update(screen_update_noop, true);
	}
	g_current_update_func();
	return previous_update_func;
}


void overlay_update_noop() {
}


void overlay_update_none() {
	g_gui_tft_overlay.fillSprite(TFT_TRANSPARENT);
}

static uint16_t data[28*28];
void overlay_update_volume() {
	g_gui_tft_overlay.fillSprite(TFT_TRANSPARENT);
	g_gui_tft_overlay.setTextColor(TFT_WHITE, TFT_TRANSPARENT);
	if(String("False").equals(g_system_settings["audio:volume-mute"])) {
		g_gui_tft_overlay.drawString("Volume: " + g_system_settings["audio:volume-level"], 80, 0);
	} else {
		g_gui_tft_overlay.drawString("Volume: mute", 80, 0);
		g_gui_tft_overlay.pushImage(0, 0, 160,30, data);
	}
}


void overlay_update_message() {
}

