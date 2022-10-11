#ifdef ARDUINO_ROUNDYPI

#include <Arduino.h>
#include <TimeLib.h>

#include "globals.h"
#include "device/board/roundypi.h"


Board::Board() {
	Serial.begin(115200);
	delay(100);
}


void Board::start(bool& host_booting) {
	uint32_t  epoch = 0;

	g_device_microcontroller.start(epoch, host_booting);
	if(epoch > 0) {
		setTime(epoch);
		g_util_webserial.send("syslog", "recovered system time from before microcontroller was resetted");
	}
	if(TFT_BL >= 0) {
		//pinMode(TFT_BL, OUTPUT);
	}
}


void Board::reset(int32_t timestamp, bool host_rebooting) {
	g_microcontroller.reset(timestamp, host_rebooting);
}


void Board::halt() {
	g_microcontroller.halt();
}


void Board::displayOn() {
	if(TFT_BL >= 0) {
		digitalWrite(TFT_BL, HIGH);
	}
}


void Board::displayOff() {
	if(TFT_BL >= 0) {
		digitalWrite(TFT_BL, LOW);
	}
}



#endif

