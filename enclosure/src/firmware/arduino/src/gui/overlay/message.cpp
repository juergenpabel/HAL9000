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
		g_gui_tft_overlay.fillRect(0, (TFT_HEIGHT/8*5)-(g_gui_tft_overlay.fontHeight()/2), TFT_WIDTH, g_gui_tft_overlay.fontHeight()/2, TFT_BLACK);
		g_gui_tft_overlay.setTextColor(TFT_WHITE, TFT_BLACK, false);
		g_gui_tft_overlay.setTextFont(1);
		g_gui_tft_overlay.setTextSize(2);
		g_gui_tft_overlay.setTextDatum(MC_DATUM);
		g_gui_tft_overlay.drawString(message, TFT_WIDTH/2, TFT_HEIGHT/8*5);
		if(force_refresh == false) {
			screen_set_refresh();
		}
	}
}

