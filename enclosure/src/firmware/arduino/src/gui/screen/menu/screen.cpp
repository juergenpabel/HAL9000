#include <string.h>
#include "gui/screen/screen.h"
#include "util/jpeg.h"
#include "globals.h"


void screen_menu(bool force_refresh) {
	static String  menu_title;
	static String  menu_item;

	if(force_refresh) {
		menu_title = String();
		menu_item  = String();
		g_gui_tft.fillScreen(TFT_BLACK);
	}
	if(menu_title.equals(g_system_settings["gui/screen:menu/title"]) == false || menu_item.equals(g_system_settings["gui/screen:menu/text"]) == false) {
		menu_title = g_system_settings["gui/screen:menu/title"];
		menu_item  = g_system_settings["gui/screen:menu/text"];
		g_gui_tft.setTextColor(TFT_WHITE, TFT_BLACK, true);
		g_gui_tft.setTextDatum(MC_DATUM);
		g_gui_tft.setTextSize(1);
		g_gui_tft.fillRect(0, (TFT_HEIGHT/8*3)-(g_gui_tft.fontHeight()/2), TFT_WIDTH, g_gui_tft.fontHeight(), TFT_BLACK);
		g_gui_tft.drawString(menu_title, TFT_WIDTH/2, TFT_HEIGHT/8*3);
		g_gui_tft.setTextSize(2);
		g_gui_tft.fillRect(0, (TFT_HEIGHT/8*4)-(g_gui_tft.fontHeight()/2), TFT_WIDTH, g_gui_tft.fontHeight(), TFT_BLACK);
		g_gui_tft.drawString(menu_item, TFT_WIDTH/2, TFT_HEIGHT/8*4);
	}
}

