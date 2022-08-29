#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "globals.h"


time_t       g_gui_screen_idle_clock_previously = 0;


void screen_idle(bool force_refresh) {
	time_t    clock_currently = now();

	if(force_refresh) {
		g_gui_tft.fillScreen(TFT_BLACK);
	}
	if(year(clock_currently) >= 2001) {
		if(g_gui_screen_idle_clock_previously == 0) {
			g_util_webserial.send("syslog", "showing clock while idle");
		}
		if(force_refresh || g_gui_screen_idle_clock_previously == 0
		                 || hour(clock_currently) != hour(g_gui_screen_idle_clock_previously)
		                 || minute(clock_currently) != minute(g_gui_screen_idle_clock_previously)) {
			char clock[6] = {0};

			g_gui_screen_idle_clock_previously = clock_currently;
			snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_currently), minute(clock_currently));
			g_gui_tft.setTextColor(TFT_WHITE, TFT_BLACK, true);
			g_gui_tft.setTextFont(1);
			g_gui_tft.setTextSize(5);
			g_gui_tft.setTextDatum(MC_DATUM);
			g_gui_tft.drawString(clock, TFT_WIDTH/2, TFT_HEIGHT/2);
		}
	}
}

