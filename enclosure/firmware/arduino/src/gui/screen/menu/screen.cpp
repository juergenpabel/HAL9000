#include "gui/screen/screen.h"
#include "util/jpeg.h"
#include "globals.h"


unsigned long gui_screen_menu(unsigned long lastDraw, TFT_eSPI* gui) {
	static etl::string<GLOBAL_VALUE_SIZE>  menu_title;
	static etl::string<GLOBAL_VALUE_SIZE>  menu_item;

	if(lastDraw == GUI_UPDATE) {
		menu_title = g_application.getEnv("gui/screen:menu/title");
		menu_item  = g_application.getEnv("gui/screen:menu/text");
		gui->fillScreen(TFT_BLACK);
		gui->setTextColor(TFT_WHITE, TFT_BLACK, true);
		gui->setTextDatum(MC_DATUM);
		gui->setTextPadding(GUI_SCREEN_WIDTH);
		gui->setTextSize(2);
		gui->drawString(menu_title.c_str(), (gui->width()-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (gui->height()-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*3);
		gui->setTextSize(3);
		gui->drawString(menu_item.c_str(), (gui->width()-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (gui->height()-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*5);
		return millis();
	}
	return lastDraw;
}

