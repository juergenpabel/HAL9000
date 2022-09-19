#include <TimeLib.h>

#include "system/microcontroller/include.h"
#include "globals.h"


void system_start() {
	uint32_t  epoch = 0;

	Serial.begin(115200);
	g_system_microcontroller.start(epoch);
	if(epoch > 0) {
		setTime(epoch);
		g_util_webserial.send("syslog", "recovered system time from before microcontroller was resetted");
	}
	pinMode(TFT_BL, OUTPUT);
	digitalWrite(TFT_BL, HIGH);
}


void system_reset() {
	uint32_t epoch = 0;

	if(year() > 2001) {
		epoch = now();
	}
	digitalWrite(TFT_BL, LOW);
	g_system_microcontroller.reset(epoch);
	while(true) {
		delay(1);
	}
}


void system_halt() {
	digitalWrite(TFT_BL, LOW);
	g_system_microcontroller.halt();
	while(true) {
		delay(1);
	}
}

