#include <TimeLib.h>
#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "globals.h"


unsigned long gui_screen_idle(unsigned long validity, TFT_eSPI* gui) {
	static time_t    clock_previous = 0;
	       time_t    clock_current = 0;
	       bool      clock_refresh = false;

	if(validity == GUI_INVALIDATED) {
		gui->fillScreen(TFT_BLACK);
		if(g_system_application.hasEnv("gui/screen:idle/clock") == true) {
			if(g_system_application.getEnv("gui/screen:idle/clock").compare("false") == 0) {
				return millis();
			}
		}
	}
	clock_current = now();
	if(hour(clock_current)!=hour(clock_previous) || minute(clock_current)!=minute(clock_previous) || second(clock_current)!=second(clock_previous)) {
		clock_refresh = true;
	}
	if(validity == GUI_INVALIDATED || clock_refresh == true) {
		char output[6] = {0};

		clock_previous = clock_current;
		if(second(clock_current) % 2 == 0) {
			snprintf(output, sizeof(output), "%02d:%02d", hour(clock_current), minute(clock_current));
		} else {
			snprintf(output, sizeof(output), "%02d %02d", hour(clock_current), minute(clock_current));
		}
		gui->setTextFont(1);
		gui->setTextSize(5);
		gui->setTextDatum(MC_DATUM);
		gui->setTextColor(TFT_RED, TFT_BLACK, true);
		if(g_system_application.hasEnv("system/features:time/synced") == true) {
			if(g_system_application.getEnv("system/features:time/synced").compare("true") == 0) {
				gui->setTextColor(TFT_WHITE, TFT_BLACK, true);
			}
		}
		gui->drawString(output, (gui->width()-GUI_SCREEN_WIDTH)+(GUI_SCREEN_WIDTH/2), (gui->height()-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/2));
		return millis();
	}
	return validity;
}

