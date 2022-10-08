#include <TimeLib.h>

#include "device/microcontroller/include.h"
#include "globals.h"


void system_start() {
	bool  host_booting = true;

	g_device_board.start(host_booting);
	if(host_booting == false) {
		g_system_runtime["system/state:app/target"] = "waiting";
		g_util_webserial.send("syslog", "host system not booting");
	}
	if(host_booting == true) {
		g_device_board.displayOn();
	}
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
	g_device_microcontroller.reset(epoch, host_rebooting);
	//this codepath should never be taken 
	g_gui.fillScreen(TFT_BLACK);
	g_gui.drawString("ERROR, halting.", TFT_WIDTH/2, TFT_HEIGHT/2);
	digitalWrite(TFT_BL, HIGH);
	while(true) {
		delay(1);
	}
}


void system_halt() {
	digitalWrite(TFT_BL, LOW);
	g_device_microcontroller.halt();
	while(true) {
		delay(1);
	}
}

