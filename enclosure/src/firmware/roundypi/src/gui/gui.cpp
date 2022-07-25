#include "globals.h"

#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui.h"
#include "frame.h"
#include "jpeg.h"


static gui_update_func current_update_func = gui_update_idle;
static time_t clock_previously = 0;


gui_update_func gui_update(gui_update_func new_update_func) {
	gui_update_func previous_update_func = NULL;

	if(new_update_func != NULL) {
		if(new_update_func == gui_update_idle) {
			clock_previously = 0;
		}
		previous_update_func = current_update_func;
		current_update_func = new_update_func;
	} else {
		current_update_func();
	}
	return previous_update_func;
}


void gui_update_idle() {
	time_t    clock_currently = now();

	if(year(clock_currently) >= 2001) {
		if(clock_previously == 0) {
			g_webserial.send("RoundyPI", "Showing clock while idle");
			g_tft.fillScreen(TFT_BLACK);
		}
		if(clock_previously == 0 || hour(clock_currently) != hour(clock_previously) || minute(clock_currently) != minute(clock_previously)) {
			char clock[6] = {0};

			clock_previously = clock_currently;
			snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_currently), minute(clock_currently));
			g_tft.drawString(clock, 120, 120);
		}
	}
}

