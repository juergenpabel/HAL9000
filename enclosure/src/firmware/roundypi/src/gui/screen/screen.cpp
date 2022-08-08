#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "gui/screen/sequence/frame.h"
#include "gui/screen/splash/jpeg.h"

#include "globals.h"


static screen_update_func current_update_func = screen_update_idle;
static time_t clock_previously = 0;


screen_update_func screen_update(screen_update_func new_update_func, bool force_refresh) {
	screen_update_func previous_update_func = NULL;
	static bool     forced_refresh = false;

	if(new_update_func == NULL && force_refresh == false) {
		force_refresh = forced_refresh;
		forced_refresh = false;
	}
	if(new_update_func != NULL) {
		if(new_update_func == screen_update_noop && force_refresh) {
			forced_refresh = true; //remember for next invocation
			return NULL;
		}
		if(force_refresh == false) {
			forced_refresh = true; //remember for next invocation
		}
		if(new_update_func == screen_update_idle) {
			clock_previously = 0;
		}
		previous_update_func = current_update_func;
		current_update_func = new_update_func;
	}
	if(force_refresh || new_update_func == NULL) {
		overlay_update(NULL);
		current_update_func(force_refresh);
		g_tft_overlay.pushSprite(TFT_WIDTH/2-g_tft_overlay.width()/2, TFT_HEIGHT/4*3-g_tft_overlay.height()/2, TFT_TRANSPARENT);
	}
	return previous_update_func;
}


void screen_update_noop(bool force_refresh) {
}


void screen_update_idle(bool force_refresh) {
	time_t    clock_currently = now();

	if(force_refresh) {
		g_tft.fillScreen(TFT_BLACK);
	}
	if(year(clock_currently) >= 2001) {
		if(clock_previously == 0) {
			g_webserial.send("syslog", "showing clock while idle");
			g_tft.fillScreen(TFT_BLACK);
		}
		if(force_refresh || clock_previously == 0 || hour(clock_currently) != hour(clock_previously) || minute(clock_currently) != minute(clock_previously)) {
			char clock[6] = {0};

			clock_previously = clock_currently;
			snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_currently), minute(clock_currently));
			g_tft.drawString(clock, 120, 120);
		}
	}
}

