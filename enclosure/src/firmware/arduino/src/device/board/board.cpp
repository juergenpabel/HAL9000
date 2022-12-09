#include <Arduino.h>
#include <TimeLib.h>

#include "globals.h"


AbstractBoard::AbstractBoard() {
}


void AbstractBoard::start(bool& host_booting) {
	g_device_microcontroller.mutex_create("Serial", true);
	Serial.begin(115200);
	delay(100);
	g_util_webserial.begin();
}


void AbstractBoard::reset(bool host_rebooting) {
	if(Serial == true) {
		Serial.println("[\"syslog/info\", \"resetting NOW.\"");
		Serial.flush();
		Serial.end();
		delay(100);
	}
	this->displayOff();
        g_device_microcontroller.reset(now(), host_rebooting);
}


void AbstractBoard::halt() {
	if(Serial == true) {
		Serial.println("[\"syslog/info\", \"halting NOW.\"");
		Serial.flush();
		Serial.end();
		delay(100);
	}
	this->displayOff();
	g_device_microcontroller.halt();
}

