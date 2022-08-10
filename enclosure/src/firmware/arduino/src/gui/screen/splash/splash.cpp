#include "globals.h"

#include <TimeLib.h>
#include "gui/screen/screen.h"

uint32_t        g_splash_timeout = 0;
screen_update_func g_previous_screen = NULL;


void screen_update_splash(bool refresh) {
	if(g_splash_timeout > 0 && now() > g_splash_timeout) {
		g_util_webserial.send("syslog", "splash timed out, reactivating previous screen");
		screen_update(g_previous_screen, true);
		g_previous_screen = NULL;
	}
}

