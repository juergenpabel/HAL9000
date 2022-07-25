#include "globals.h"

#include <TimeLib.h>
#include "gui.h"

uint32_t        g_splash_timeout = 0;
gui_update_func g_previous_gui = NULL;


void gui_update_splash() {
	if(g_splash_timeout > 0 && now() > g_splash_timeout) {
		g_webserial.send("RoundyPI", "splash timed out, reactivating previous gui");
		gui_update(g_previous_gui);
		g_previous_gui = NULL;
	}
}

