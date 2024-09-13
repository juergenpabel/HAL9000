#include <LittleFS.h>
#include <TimeLib.h>

#include "globals.h"


bool AbstractBoard::start() {
	uint32_t  epoch = 0;

	g_util_webserial.begin();
	g_device_microcontroller.start(epoch);
	g_device_microcontroller.mutex_create("gpio");
	if(epoch > 0) {
		g_util_webserial.send("syslog/debug", "recovered system time from before microcontroller was resetted");
		setTime(epoch);
	} else {
                g_util_webserial.send("syslog/debug", "system was hard-resetted or powered-on, unknown system time");
	}
	if(LittleFS.begin() != true) {
		g_application.notifyError("critical", "212", "Filesystem error", "littlefs could not be started/mounted");
		return false;
	}
	return true;
}


void AbstractBoard::reset() {
	LittleFS.end();
	if(static_cast<bool>(Serial) == true) {
		Serial.write("[\"syslog/info\", \"Arduino resetting NOW.\"]\n");
		Serial.flush();
		Serial.end();
		delay(100);
	}
	g_device_microcontroller.reset(now());
}


void AbstractBoard::halt() {
	LittleFS.end();
	if(static_cast<bool>(Serial) == true) {
		Serial.write("[\"syslog/info\", \"Arduino halting NOW.\"]\n");
		Serial.flush();
		Serial.end();
		delay(100);
	}
	g_device_microcontroller.halt();
}

