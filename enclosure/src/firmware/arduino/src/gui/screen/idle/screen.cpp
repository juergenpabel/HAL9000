#include <string>
#include <TimeLib.h>
#include "gui/screen/screen.h"
#include "globals.h"


void gui_screen_idle(bool refresh) {
	static time_t  clock_previous = 0;
	       time_t  clock_current = now();
	       bool    clock_show = true;

	if(refresh) {
		clock_previous = 0;
		g_gui_tft.fillScreen(TFT_BLACK);
	}
	if(g_system_runtime.count("gui/screen:idle/clock") == 1) {
		if(g_system_runtime["gui/screen:idle/clock"] == std::string("false")) {
			clock_show = false;
		}
	}
	if(clock_show == true && year(clock_current) >= 2001) {
		if(hour(clock_current) != hour(clock_previous) || minute(clock_current) != minute(clock_previous)) {
			char clock[6] = {0};

			clock_previous = clock_current;
			snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_current), minute(clock_current));
			g_gui_tft.setTextColor(TFT_WHITE, TFT_BLACK, true);
			g_gui_tft.setTextFont(1);
			g_gui_tft.setTextSize(5);
			g_gui_tft.setTextDatum(MC_DATUM);
			g_gui_tft.drawString(clock, TFT_WIDTH/2, TFT_HEIGHT/2);
		}
	}
}

