#ifndef __DEVICE_BOARD_M5CORE2_H__
#define __DEVICE_BOARD_M5CORE2_H__

#ifdef ARDUINO_M5STACK_Core2

#include "device/board/board.h"

class Board : public AbstractBoard {
	public:
		Board();
		virtual bool start();
		virtual bool configure(const JsonVariant& configuration);
		virtual void reset();
		virtual void halt();

		virtual bool isDisplay(bool status);
		virtual void displayOn();
                virtual void displayOff();
};

#endif

#endif

