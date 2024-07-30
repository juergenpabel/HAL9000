#include <TimeLib.h>
#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "globals.h"


gui_refresh_t gui_screen_idle(bool refresh) {
	static time_t    clock_previous = 0;
	       time_t    clock_current = now();
	       bool      clock_show = true;
	       bool      clock_synced = false;
               TFT_eSPI* gui;
	       gui_refresh_t gui_refresh = RefreshIgnore;

	gui = &g_gui_screen;
	if(g_gui_screen.getPointer() == nullptr) {
		gui = &g_gui;
		g_util_webserial.send("syslog/debug", "gui_screen_idle() using direct rendering because no screen-sprite");
	}
	if(refresh == true) {
		clock_previous = 0;
		gui->fillScreen(TFT_BLACK);
	}
	if(g_application.hasEnv("gui/screen:idle/clock") == true) {
		if(g_application.getEnv("gui/screen:idle/clock").compare("false") == 0) {
			clock_show = false;
		}
	}
	if(g_application.hasEnv("application/runtime:time/synced") == true) {
		if(g_application.getEnv("application/runtime:time/synced").compare("true") == 0) {
			clock_synced = true;
		}
	}
	if(clock_show == true && year(clock_current) >= 2001) {
		if(hour(clock_current) != hour(clock_previous) || minute(clock_current) != minute(clock_previous)) {
			char clock[6] = {0};

			clock_previous = clock_current;
			snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_current), minute(clock_current));
			gui->setTextFont(1);
			gui->setTextSize(5);
			gui->setTextDatum(MC_DATUM);
			if(clock_synced == true) {
				gui->setTextColor(TFT_WHITE, TFT_BLACK, true);
			} else {
				gui->setTextColor(TFT_RED, TFT_BLACK, true);
			}
			gui->drawString(clock, (gui->width()-GUI_SCREEN_WIDTH)+(GUI_SCREEN_WIDTH/2), (gui->height()-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/2));
			if(gui == &g_gui_screen) {
				gui_refresh = RefreshScreen;
			}
		}
	}
	return gui_refresh;
}

