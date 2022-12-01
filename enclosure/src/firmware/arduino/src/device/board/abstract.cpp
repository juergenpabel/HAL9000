#include <Arduino.h>

#include "globals.h"


AbstractBoard::AbstractBoard() {
}


void AbstractBoard::start(bool& host_booting) {
	g_device_microcontroller.mutex_create("Serial", true);
	Serial.begin(115200);
	delay(100);
	g_util_webserial.begin();
}

