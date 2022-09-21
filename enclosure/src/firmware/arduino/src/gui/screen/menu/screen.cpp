#include "gui/screen/screen.h"
#include "util/jpeg.h"
#include "globals.h"


void gui_screen_menu(bool refresh) {
	static etl::string<GLOBAL_VALUE_SIZE>  menu_title;
	static etl::string<GLOBAL_VALUE_SIZE>  menu_item;

	if(refresh) {
		menu_title.clear();
		menu_item.clear();
		g_device_tft.fillScreen(TFT_BLACK);
	}
	if(menu_title != g_system_runtime["gui/screen:menu/title"] || menu_item != g_system_runtime["gui/screen:menu/text"]) {
		menu_title = g_system_runtime["gui/screen:menu/title"];
		menu_item  = g_system_runtime["gui/screen:menu/text"];
		g_device_tft.setTextColor(TFT_WHITE, TFT_BLACK, true);
		g_device_tft.setTextDatum(MC_DATUM);
		g_device_tft.setTextSize(1);
		g_device_tft.fillRect(0, (TFT_HEIGHT/8*3)-(g_device_tft.fontHeight()/2), TFT_WIDTH, g_device_tft.fontHeight(), TFT_BLACK);
		g_device_tft.drawString(menu_title.c_str(), TFT_WIDTH/2, TFT_HEIGHT/8*3);
		g_device_tft.setTextSize(2);
		g_device_tft.fillRect(0, (TFT_HEIGHT/8*4)-(g_device_tft.fontHeight()/2), TFT_WIDTH, g_device_tft.fontHeight(), TFT_BLACK);
		g_device_tft.drawString(menu_item.c_str(), TFT_WIDTH/2, TFT_HEIGHT/8*4);
	}
}

