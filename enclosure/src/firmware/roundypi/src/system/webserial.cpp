#include "globals.h"
#include <TimeLib.h>
#include "webserial.h"
#include "system.h"

static volatile long g_sync_secs = -1;


void on_system_config(JSONVar parameter) {
	//TODO
}


time_t time_sync() {
	uint32_t timeout = 0;

	g_sync_secs = 0;
	g_webserial.sendEvent("system:time");
	timeout = millis() + 1000;
	while(g_sync_secs == 0 && millis() < timeout) {
		g_webserial.check();
		delay(10);
	}
	return g_sync_secs;
}


void on_system_time(JSONVar parameter) {
	int interval = 3600;

	if(g_sync_secs == -1) {
		if(parameter.hasOwnProperty("interval")) {
			interval = parameter["interval"];
		}
		setSyncProvider(time_sync);
		setSyncInterval(interval);
	}
	if(parameter.hasOwnProperty("epoch-seconds")) {
		g_sync_secs = parameter["epoch-seconds"];
	}
}


void on_system_reset(JSONVar parameter) {
	int delay_ms = 0;

	if(parameter.hasOwnProperty("delay")) {
		delay_ms = parameter["delay"];
	}
	g_webserial.send("RoundyPI", "Resetting RP2040...");
	system_reset(delay_ms);
}


void on_system_flash(JSONVar parameter) {
	int delay_ms = 0;

	if(parameter.hasOwnProperty("delay")) {
		delay_ms = parameter["delay"];
	}
	g_webserial.send("RoundyPI", "Rebooting RP2040 to UF2");
	system_flash(delay_ms);
}

