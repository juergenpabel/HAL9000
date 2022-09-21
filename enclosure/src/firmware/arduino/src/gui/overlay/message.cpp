#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


void gui_overlay_message(bool refresh) {
	static etl::string<GLOBAL_VALUE_SIZE>  message;

	if(refresh) {
		message.clear();
	}
	if(message.compare(g_system_runtime["gui/overlay:message/text"]) != 0) {
		message = g_system_runtime["gui/overlay:message/text"];
		g_device_tft_overlay.fillRect(0, (TFT_HEIGHT/8*5)-(g_device_tft_overlay.fontHeight()/2), TFT_WIDTH, g_device_tft_overlay.fontHeight()/2, TFT_BLACK);
		g_device_tft_overlay.setTextColor(TFT_WHITE, TFT_BLACK, false);
		g_device_tft_overlay.setTextFont(1);
		g_device_tft_overlay.setTextSize(2);
		g_device_tft_overlay.setTextDatum(MC_DATUM);
		g_device_tft_overlay.drawString(message.c_str(), TFT_WIDTH/2, TFT_HEIGHT/8*5);
		if(refresh == false) {
			gui_screen_set_refresh();
		}
	}
}

