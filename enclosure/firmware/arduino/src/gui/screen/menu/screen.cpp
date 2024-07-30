#include "gui/screen/screen.h"
#include "util/jpeg.h"
#include "globals.h"


gui_refresh_t gui_screen_menu(bool refresh) {
	static etl::string<GLOBAL_VALUE_SIZE>  menu_title;
	static etl::string<GLOBAL_VALUE_SIZE>  menu_item;
	       TFT_eSPI* gui;
	       gui_refresh_t gui_refresh = RefreshIgnore;

	gui = &g_gui_screen;
	if(g_gui_screen.getPointer() == nullptr) {
		gui = &g_gui;
		g_util_webserial.send("syslog/debug", "gui_screen_menu() using direct rendering because no screen-sprite");
	}
	if(refresh == true) {
		menu_title.clear();
		menu_item.clear();
		gui->fillScreen(TFT_BLACK);
	}
	if(menu_title != g_application.getEnv("gui/screen:menu/title") || menu_item != g_application.getEnv("gui/screen:menu/text")) {
		menu_title = g_application.getEnv("gui/screen:menu/title");
		menu_item  = g_application.getEnv("gui/screen:menu/text");
		gui->setTextColor(TFT_WHITE, TFT_BLACK, true);
		gui->setTextDatum(MC_DATUM);
		gui->setTextPadding(GUI_SCREEN_WIDTH);
		gui->setTextSize(2);
		gui->drawString(menu_title.c_str(), (gui->width()-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (gui->height()-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*3);
		gui->setTextSize(3);
		gui->drawString(menu_item.c_str(), (gui->width()-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (gui->height()-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*5);
		if(gui == &g_gui_screen) {
			gui_refresh = RefreshScreen;
		}
	}
	return gui_refresh;
}

