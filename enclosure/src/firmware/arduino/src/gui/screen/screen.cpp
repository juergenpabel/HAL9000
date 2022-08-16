#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "gui/screen/hal9000/frame.h"
#include "gui/screen/splash/jpeg.h"

#include "globals.h"


static screen_func  g_screen = screen_idle;
static bool         g_screen_forced_refresh = false;
static time_t       g_clock_previously = 0;


screen_func screen_get() {
	return g_screen;
}


screen_func screen_set(screen_func new_screen) {
	screen_func previous_screen;

	previous_screen = g_screen;
	if(new_screen != NULL) {
		g_screen = new_screen;
		g_screen_forced_refresh = true;
		if(new_screen == screen_idle) {
			g_clock_previously = 0;
		}
	}
	return previous_screen;
}


void screen_update(bool force_refresh) {
	if(force_refresh == false) {
		force_refresh = g_screen_forced_refresh;
		g_screen_forced_refresh = false;
	}
	overlay_update(force_refresh);
	g_screen(force_refresh);
	g_gui_tft_overlay.pushSprite(0, 0, TFT_BLACK);
}


void screen_idle(bool force_refresh) {
	time_t    clock_currently = now();

	if(year(clock_currently) >= 2001) {
		if(g_clock_previously == 0) {
			g_util_webserial.send("syslog", "showing clock while idle");
			g_gui_tft.fillScreen(TFT_BLACK);
		}
		if(force_refresh || g_clock_previously == 0 || hour(clock_currently) != hour(g_clock_previously) || minute(clock_currently) != minute(g_clock_previously)) {
			char clock[6] = {0};

			g_clock_previously = clock_currently;
			snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_currently), minute(clock_currently));
			g_gui_tft.fillScreen(TFT_BLACK);
			g_gui_tft.drawString(clock, 120, 120-g_gui_tft.fontHeight()/2);
		}
	}
}

