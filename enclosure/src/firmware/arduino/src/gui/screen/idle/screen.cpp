#include <TimeLib.h>
#include "gui/screen/screen.h"
#include "globals.h"


void gui_screen_idle(bool refresh) {
	static time_t  clock_previous = 0;
	       time_t  clock_current = now();
	       bool    clock_show = true;
	       bool    clock_synced = true;

	if(refresh) {
		clock_previous = 0;
		g_gui.fillScreen(TFT_BLACK);
	}
	if(g_application.hasEnv("gui/screen:idle/clock") == true) {
		if(g_application.getEnv("gui/screen:idle/clock").compare("false") == 0) {
			clock_show = false;
		}
	}
	if(g_application.hasEnv("application/runtime#time") == true) {
		if(g_application.getEnv("application/runtime#time").compare("unsynced") == 0) {
			clock_synced = false;
		}
	}
	if(clock_show == true && year(clock_current) >= 2001) {
		if(hour(clock_current) != hour(clock_previous) || minute(clock_current) != minute(clock_previous)) {
			char clock[6] = {0};

			clock_previous = clock_current;
			snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_current), minute(clock_current));
			g_gui.setTextFont(1);
			g_gui.setTextSize(5);
			g_gui.setTextDatum(MC_DATUM);
			if(clock_synced == true) {
				g_gui.setTextColor(TFT_WHITE, TFT_BLACK, true);
			} else {
				g_gui.setTextColor(TFT_RED, TFT_BLACK, true);
			}
			g_gui.drawString(clock, (TFT_WIDTH-GUI_SCREEN_WIDTH)+(GUI_SCREEN_WIDTH/2), (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/2));
		}
	}
}

