#include "globals.h"

#include <TimeLib.h>
#include "gui/screen/screen.h"

screen_func  g_previous_screen = NULL;


void screen_splash(bool force_refresh) {
	if(false /*TODO*/) {
		g_util_webserial.send("syslog", "screen_splash() reactivating previous screen");
		screen_set(g_previous_screen);
		g_previous_screen = NULL;
	}
}

