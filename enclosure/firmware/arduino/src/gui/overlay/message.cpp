#include <etl/string.h>
#include <etl/map.h>

#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, uint32_t, 8> ColorMap;
static ColorMap g_colors = {{"black",  TFT_BLACK},
                            {"white",  TFT_WHITE},
                            {"red",    TFT_RED},
                            {"green",  TFT_GREEN},
                            {"blue",   TFT_BLUE},
                            {"yellow", TFT_YELLOW},
                            {"orange", TFT_ORANGE},
                            {"grey",   TFT_DARKGREY}};


unsigned long gui_overlay_message(unsigned long validity, TFT_eSPI* gui) {
	static etl::string<GLOBAL_VALUE_SIZE>  text;
	static uint32_t                        text_color;
	static uint32_t                        text_bgcolor;
	static int32_t                         text_vertical;
	static int32_t                         text_horizontal;
	static uint8_t                         text_datum;

	if(validity == GUI_INVALIDATED || g_system_application.hasEnv("gui/overlay:message/text") == true) {
		if(g_system_application.hasEnv("gui/overlay:message/text") == true) {
			text = g_system_application.getEnv("gui/overlay:message/text");
			text_color = TFT_WHITE;
			text_bgcolor = TFT_BLACK;
			text_vertical = (gui->height()-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/2);
			text_horizontal = (gui->width()-GUI_SCREEN_WIDTH)/2+(GUI_SCREEN_WIDTH/2);
			text_datum = MC_DATUM;
			g_system_application.delEnv("gui/overlay:message/text");
		}
		if(g_system_application.hasEnv("gui/overlay:message/text-color") == true) {
			ColorMap::iterator iter = g_colors.find(g_system_application.getEnv("gui/overlay:message/text-color"));
			if(iter != g_colors.end()) {
				text_color = iter->second;
			}
			g_system_application.delEnv("gui/overlay:message/text-color");
		}
		if(g_system_application.hasEnv("gui/overlay:message/text-bgcolor") == true) {
			ColorMap::iterator iter = g_colors.find(g_system_application.getEnv("gui/overlay:message/text-bgcolor"));
			if(iter != g_colors.end()) {
				text_bgcolor = iter->second;
			}
			g_system_application.delEnv("gui/overlay:message/text-bgcolor");
		}
		if(g_system_application.hasEnv("gui/overlay:message/position-vertical") == true) {
			if(g_system_application.getEnv("gui/overlay:message/position-vertical").compare("above") == 0) {
				text_vertical = (gui->height()-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*3);
				text_datum = TC_DATUM;
			}
			if(g_system_application.getEnv("gui/overlay:message/position-vertical").compare("below") == 0) {
				text_vertical = (gui->height()-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*5);
				text_datum = BC_DATUM;
			}
			g_system_application.delEnv("gui/overlay:message/position-vertical");
		}
		if(g_system_application.hasEnv("gui/overlay:message/position-horizontal") == true) {
			if(g_system_application.getEnv("gui/overlay:message/position-horizontal").compare("left") == 0) {
				text_horizontal = (gui->width()-GUI_SCREEN_WIDTH)/2;
				text_datum -= 1;
			}
			if(g_system_application.getEnv("gui/overlay:message/position-horizontal").compare("right") == 0) {
				text_horizontal = gui->width() - (gui->width()-GUI_SCREEN_WIDTH)/2;
				text_datum += 1;
			}
			g_system_application.delEnv("gui/overlay:message/position-horizontal");
		}
		gui->setTextColor(text_color, text_bgcolor, false);
		gui->setTextFont(1);
		gui->setTextSize(2);
		gui->setTextDatum(text_datum);
		gui->drawString(text.c_str(), text_horizontal, text_vertical);
		return millis();
	}
	return validity;
}

