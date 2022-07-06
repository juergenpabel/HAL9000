#include "defines.h"
#include "types.h"
#include "globals.h"
#include <TimeLib.h>


static volatile long g_sync_secs = -1;


time_t time_sync() {
	uint32_t timeout = 0;

	if(g_sync_secs == -1) {
		setSyncInterval(3600);
		setSyncProvider(time_sync);
	}
	g_sync_secs = 0;
	g_webserial.sendEvent("time:sync");
	timeout = millis() + 1000;
	while(g_sync_secs == 0 && millis() < timeout) {
		g_webserial.check();
		delay(10);
	}
	return g_sync_secs;
}


void on_time_sync(JSONVar parameter) {
	g_sync_secs = parameter["epoch-seconds"];
}

