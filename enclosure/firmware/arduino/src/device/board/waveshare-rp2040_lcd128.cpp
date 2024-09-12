#ifdef ARDUINO_WAVESHARE_RP2040_LCD128

#include <Arduino.h>
#include <TimeLib.h>

#include "device/board/waveshare-rp2040_lcd128.h"
#include "globals.h"


Board::Board()
      :AbstractBoard("waveshare-rp2040_lcd128") {
}


bool Board::start() {
	if(AbstractBoard::start() == false) {
		return false;
	}
	if(TFT_BL >= 0) {
		pinMode(TFT_BL, OUTPUT);
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

