#include <TimeLib.h>

#include "system/microcontroller/include.h"
#include "globals.h"


void system_start() {
	uint32_t  epoch = 0;
	bool      host_booting = true;

	Serial.begin(115200);
	g_system_microcontroller.start(epoch, host_booting);
	if(epoch > 0) {
		setTime(epoch);
		g_util_webserial.send("syslog", "recovered system time from before microcontroller was resetted");
	}
	if(host_booting == false) {
		g_system_runtime["system/state:app/target"] = "waiting";
		g_util_webserial.send("syslog", "host system not booting");
	}
	pinMode(TFT_BL, OUTPUT);
	digitalWrite(TFT_BL, HIGH);
}


void system_reset() {
	uint32_t  epoch = 0;
	bool      host_rebooting = false;

	if(year() > 2001) {
		epoch = now();
	}
	if(g_system_runtime["system/state:app/target"].compare("rebooting") == 0) {
		host_rebooting = true;
	}
	digitalWrite(TFT_BL, LOW);
	g_system_microcontroller.reset(epoch, host_rebooting);
	//this codepath should never be taken 
	g_device_tft.fillScreen(TFT_BLACK);
	g_device_tft.drawString("ERROR, halting.", TFT_WIDTH/2, TFT_HEIGHT/2);
	digitalWrite(TFT_BL, HIGH);
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

