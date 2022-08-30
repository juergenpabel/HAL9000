#include <string>
#include "gui/screen/screen.h"
#include "util/jpeg.h"
#include "globals.h"


void gui_screen_menu(bool force_refresh) {
	static std::string  menu_title;
	static std::string  menu_item;

	if(force_refresh) {
		menu_title = std::string();
		menu_item  = std::string();
		g_gui_tft.fillScreen(TFT_BLACK);
	}
	if(menu_title != g_system_status["gui/screen:menu/title"] || menu_item != g_system_status["gui/screen:menu/text"]) {
		menu_title = g_system_status["gui/screen:menu/title"];
		menu_item  = g_system_status["gui/screen:menu/text"];
		g_gui_tft.setTextColor(TFT_WHITE, TFT_BLACK, true);
		g_gui_tft.setTextDatum(MC_DATUM);
		g_gui_tft.setTextSize(1);
		g_gui_tft.fillRect(0, (TFT_HEIGHT/8*3)-(g_gui_tft.fontHeight()/2), TFT_WIDTH, g_gui_tft.fontHeight(), TFT_BLACK);
		g_gui_tft.drawString(menu_title.c_str(), TFT_WIDTH/2, TFT_HEIGHT/8*3);
		g_gui_tft.setTextSize(2);
		g_gui_tft.fillRect(0, (TFT_HEIGHT/8*4)-(g_gui_tft.fontHeight()/2), TFT_WIDTH, g_gui_tft.fontHeight(), TFT_BLACK);
		g_gui_tft.drawString(menu_item.c_str(), TFT_WIDTH/2, TFT_HEIGHT/8*4);
	}
}

