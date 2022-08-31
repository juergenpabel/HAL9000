#include <JSONVar.h>
#include "system/time.h"
#include "globals.h"


static volatile long g_sync_epoch_secs = 0;


void system_time_set(long epoch) {
	g_sync_epoch_secs = epoch;
}


time_t system_time_sync() {
	JSONVar  request;
	uint32_t timeout;

	g_sync_epoch_secs = 0;
	request["sync"] = JSONVar();
	request["sync"]["format"] = "epoch";

	g_util_webserial.send("system/time", request);
	timeout = millis() + 1000;
	while(g_sync_epoch_secs == 0 && millis() < timeout) {
		g_util_webserial.check();
		sleep_ms(100);
	}
	return g_sync_epoch_secs;
}

