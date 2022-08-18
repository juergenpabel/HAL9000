#include <string.h>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


void overlay_message(bool force_refresh) {
	static String  message;

	if(force_refresh) {
		message = String();
	}
	if(message.equals(g_system_settings["gui/overlay:message/text"]) == false) {
		message = g_system_settings["gui/overlay:message/text"];
		g_gui_tft_overlay.fillRect(0, g_system_settings["gui/overlay:message/position_y"].toInt()-(g_gui_tft_overlay.fontHeight()/2), TFT_WIDTH, g_gui_tft_overlay.fontHeight()/2, TFT_BLACK);
		g_gui_tft_overlay.drawString(message, TFT_WIDTH/2, g_system_settings["gui/overlay:message/position_y"].toInt()-(g_gui_tft_overlay.fontHeight()/2));
		if(force_refresh == false) {
			screen_set_refresh();
		}
	}
}

