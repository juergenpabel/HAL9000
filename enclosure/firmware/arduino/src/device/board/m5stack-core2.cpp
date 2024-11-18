#ifdef ARDUINO_M5STACK_Core2

#include <Arduino.h>
#include <FS.h>
#include <LittleFS.h>
#include <TimeLib.h>

#include "globals.h"
#include "device/board/m5stack-core2.h"


Board::Board()
      :AbstractBoard("m5stack-core2")
      ,m_PMU() {
}


bool Board::start() {
	if(AbstractBoard::start() == false) {
		return false;
	}
	if(this->m_PMU.init(Wire1, 21, 22, AXP2101_SLAVE_ADDRESS) != true) {
		g_system_application.processError("panic", "211", "Board error", "m5stack-core2: PMU.init() failed");
		return false;
	}
	this->displayOn();
	return true;
}


bool Board::configure(const JsonVariant& configuration) {
	return g_device_microcontroller.configure(configuration);
}


void Board::reset() {
	AbstractBoard::reset();
}


void Board::halt() {
	this->displayOff();
	AbstractBoard::halt();
}


bool Board::isDisplay(bool status) {
	return this->m_PMU.isEnableBLDO1() == status;
}


void Board::displayOn() {
	this->m_PMU.enableBLDO1();
	g_gui.writecommand(0x11);
	delay(120);
}


void Board::displayOff() {
	g_gui.writecommand(0x10);
	delay(10);
	this->m_PMU.disableBLDO1();
}

#endif

