#include "gui/screen/screen.h"
#include "util/jpeg.h"
#include "globals.h"


void gui_screen_menu(bool refresh) {
	static etl::string<GLOBAL_VALUE_SIZE>  menu_title;
	static etl::string<GLOBAL_VALUE_SIZE>  menu_item;

	if(refresh == true) {
		menu_title.clear();
		menu_item.clear();
		g_gui.fillScreen(TFT_BLACK);
	}
	if(menu_title != g_application.getEnv("gui/screen:menu/title") || menu_item != g_application.getEnv("gui/screen:menu/text")) {
		menu_title = g_application.getEnv("gui/screen:menu/title");
		menu_item  = g_application.getEnv("gui/screen:menu/text");
		g_gui.setTextColor(TFT_WHITE, TFT_BLACK, true);
		g_gui.setTextDatum(MC_DATUM);
		g_gui.setTextPadding(GUI_SCREEN_WIDTH);
		g_gui.setTextSize(2);
		g_gui.drawString(menu_title.c_str(), (TFT_WIDTH-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*3);
		g_gui.setTextSize(3);
		g_gui.drawString(menu_item.c_str(), (TFT_WIDTH-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*5);
	}
}

