#include <LittleFS.h>
#include <TimeLib.h>

#include "globals.h"


void AbstractBoard::start(bool& host_booting) {
	uint32_t  epoch = 0;

	g_util_webserial.begin();
	g_device_microcontroller.start(epoch, host_booting);
	if(epoch > 0) {
		setTime(epoch);
		g_util_webserial.send("syslog/debug", "recovered system time from before microcontroller was resetted");
	}
	if(LittleFS.begin() != true) {
		while(true) {
			if(Serial == true) {
				Serial.println("[\"syslog/fatal\", \"LittleFS.begin() failed, halting.\"]");
			}
			delay(1000);
		}
	}
}


void AbstractBoard::reset(bool host_rebooting) {
	LittleFS.end();
	if(Serial == true) {
		Serial.println("[\"syslog/info\", \"resetting NOW.\"");
		Serial.flush();
		Serial.end();
		delay(100);
	}
	g_device_microcontroller.reset(now(), host_rebooting);
}


void AbstractBoard::halt() {
	LittleFS.end();
	if(Serial == true) {
		Serial.println("[\"syslog/info\", \"halting NOW.\"");
		Serial.flush();
		Serial.end();
		delay(100);
	}
	g_device_microcontroller.halt();
}

