#ifdef ARDUINO_M5STACK_Core2

#define XPOWERS_CHIP_AXP192

#include <Arduino.h>
#include <LittleFS.h>
#include <XPowersLib.h>

#include "globals.h"
#include "device/board/m5stack-core2.h"

static XPowersPMU PMU;

Board::Board()
      :AbstractBoard() {
}


void Board::start(bool& host_booting) {
	AbstractBoard::start(host_booting);
	if(LittleFS.begin() != true) {
		while(true) {
			if(Serial) {
				Serial.println("[\"syslog/fatal\", \"LittleFS.begin(), halting.\"]");
			}
			delay(1000);
		}
	}
	if(PMU.begin(Wire1, AXP192_SLAVE_ADDRESS, 21, 22) != true) {
		Serial.println("[\"syslog/error\", \"PMU.begin() failed\"");
		return;
	}
	PMU.setSysPowerDownVoltage(2700);
	PMU.setVbusVoltageLimit(XPOWERS_AXP192_VBUS_VOL_LIM_4V5);
	PMU.setVbusCurrentLimit(XPOWERS_AXP192_VBUS_CUR_LIM_OFF);
	PMU.disableDC2();
	PMU.disableDC3();
	PMU.disableLDO2();
	delay(100);
	PMU.pinMode(PMU_GPIO4, OUTPUT);
	PMU.digitalWrite(PMU_GPIO4, 1);
	PMU.setDC2Voltage(3300); //display
	PMU.setDC3Voltage(2800); //backlight
	PMU.setLDO2Voltage(3300); //display
	PMU.enableDC2();
	PMU.enableDC3();
	PMU.enableLDO2();
	delay(100);
}


void Board::reset(uint32_t timestamp, bool host_rebooting) {
	if(Serial) {
		Serial.println("[\"syslog/info\", \"resetting NOW.\"");
		Serial.flush();
		delay(100);
	}
	g_device_microcontroller.reset(timestamp, host_rebooting);
}


void Board::halt() {
	if(Serial) {
		Serial.println("[\"syslog/info\", \"halting NOW.\"");
		Serial.flush();
		delay(100);
	}
	this->displayOff();
	g_device_microcontroller.halt();
}


void Board::displayOn() {
	PMU.enableDC3();
	g_gui.writecommand(0x11);
	delay(120);
}


void Board::displayOff() {
	g_gui.writecommand(0x10);
	PMU.disableDC3();
	delay(10);
}


#endif

