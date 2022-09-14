#include <ArduinoJson.h>

#include "system/time.h"
#include "globals.h"


static volatile long g_sync_epoch_secs = 0;


void system_time_set(long epoch) {
	g_sync_epoch_secs = epoch;
}


time_t system_time_sync() {
	static StaticJsonDocument<256> request;
	uint32_t timeout;

	request.clear();
	request.createNestedObject("sync");
	request["sync"]["format"] = "epoch";

	g_sync_epoch_secs = 0;
	g_util_webserial.send("system/time", request.as<JsonVariant>());
	timeout = millis() + 1000;
	while(g_sync_epoch_secs == 0 && millis() < timeout) {
		g_util_webserial.update();
		sleep_ms(100);
	}
	return g_sync_epoch_secs;
}

