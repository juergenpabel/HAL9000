#include <string.h>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


void overlay_menu(bool force_refresh) {
	static String  menu_item;

	if(force_refresh) {
		menu_item = String();
	}
	if(menu_item.equals(g_system_settings["gui/overlay:menu_item/text"]) == false) {
		menu_item = g_system_settings["gui/overlay:menu_item/text"];
		g_gui_tft_overlay.fillRect(0, (TFT_HEIGHT/4*3)-(g_gui_tft_overlay.fontHeight()/2), TFT_WIDTH, g_gui_tft_overlay.fontHeight()/2, TFT_BLACK);
		g_gui_tft_overlay.drawString(menu_item, TFT_WIDTH/2, (TFT_HEIGHT/4*3)-(g_gui_tft_overlay.fontHeight()/2));
		if(force_refresh == false) {
			screen_set_refresh();
		}
	}
}

