#ifndef __DEVICE_BOARD_WAVESHARE_RP2040_LCD128_H__
#define __DEVICE_BOARD_WAVESHARE_RP2040_LCD128_H__

#ifdef ARDUINO_WAVESHARE_RP2040_LCD128

#include "device/board/board.h"


class Board : public AbstractBoard {
	public:
		Board();
		virtual bool start();
		virtual bool configure(const JsonVariant& configuration);
		virtual void reset();
		virtual void halt();

		virtual void displayOn();
                virtual void displayOff();
};

#endif

#endif
