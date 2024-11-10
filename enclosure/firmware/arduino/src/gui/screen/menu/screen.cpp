#include "gui/screen/screen.h"
#include "util/jpeg.h"
#include "globals.h"


unsigned long gui_screen_menu(unsigned long validity, TFT_eSPI* gui) {
	static etl::string<GLOBAL_VALUE_SIZE>  menu_title;
	static etl::string<GLOBAL_VALUE_SIZE>  menu_item;

	if(validity == GUI_INVALIDATED) {
		menu_title = g_system_application.getEnv("gui/screen:menu/title");
		menu_item  = g_system_application.getEnv("gui/screen:menu/text");
		gui->fillScreen(TFT_BLACK);
		gui->setTextColor(TFT_WHITE, TFT_BLACK, true);
		gui->setTextDatum(MC_DATUM);
		gui->setTextPadding(GUI_SCREEN_WIDTH);
		gui->setTextSize(2);
		gui->drawString(menu_title.c_str(), (gui->width()-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (gui->height()-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*3);
		gui->setTextSize(3);
		if(gui->textWidth(menu_item.c_str()) > GUI_SCREEN_WIDTH) {
			size_t  menu_item_lines;
			size_t  menu_item_offset_start;
			size_t  menu_item_offset_prevspace;
			size_t  menu_item_offset_nextspace;

			menu_item_lines = 1;
			menu_item_offset_start = 0;
			menu_item_offset_prevspace = menu_item.npos;
			menu_item_offset_nextspace = menu_item.find(' ', menu_item_offset_start);
			if(menu_item.back() != ' ') {
				menu_item.push_back(' '); // add explicit space character at the end for simpler loop logic below
			}
			while(menu_item_offset_nextspace != menu_item.npos) {
				if(gui->textWidth(menu_item.substr(menu_item_offset_start, menu_item_offset_nextspace-menu_item_offset_start).c_str()) > GUI_SCREEN_WIDTH) {
					menu_item_lines++;
					if(menu_item_offset_prevspace == menu_item.npos) {
						menu_item_offset_prevspace = menu_item_offset_nextspace;
					}
					menu_item[menu_item_offset_prevspace] = '\n';
					menu_item_offset_start = menu_item_offset_prevspace + 1;
					menu_item_offset_prevspace = menu_item.npos;
				} else {
					menu_item_offset_prevspace = menu_item_offset_nextspace;
				}
				menu_item_offset_nextspace = menu_item.find(' ', menu_item_offset_nextspace+1);
			}
			if(menu_item_offset_prevspace != menu_item.npos) {
				menu_item[menu_item_offset_prevspace] = '\n';
			}
			menu_item.pop_back(); // remove extra space character from above
			menu_item.push_back('\n'); // extra linefeed at the end for simpler loop logic below
			menu_item_offset_start = 0;
			for(size_t i=0; i<menu_item_lines; i++) {
				size_t  menu_item_offset_newline;

				menu_item_offset_newline = menu_item.find('\n', menu_item_offset_start);
				gui->drawString(menu_item.substr(menu_item_offset_start, menu_item_offset_newline-menu_item_offset_start).c_str(), \
				                                 (gui->width()-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, \
				                                 (gui->height()-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*4 + i*(gui->fontHeight()+5));
				menu_item_offset_start = menu_item_offset_newline + 1;
			}
			menu_item.pop_back(); // remove extra linefeed character from above
		} else {
			gui->drawString(menu_item.c_str(), (gui->width()-GUI_SCREEN_WIDTH)/2+GUI_SCREEN_WIDTH/2, (gui->height()-GUI_SCREEN_HEIGHT)/2+GUI_SCREEN_HEIGHT/8*4);
		}
		return millis();
	}
	return validity;
}

