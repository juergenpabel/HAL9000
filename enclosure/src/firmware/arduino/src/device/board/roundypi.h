#ifndef __DEVICE_BOARD_ROUNDYPI_H__
#define __DEVICE_BOARD_ROUNDYPI_H__

#ifdef ARDUINO_ROUNDYPI

#include "device/board/board.h"


class Board : AbstractBoard {
	public:
		Board();
		virtual void start(bool& host_booting);
		virtual void reset(int32_t timestamp, bool host_rebooting);
		virtual void halt();

		virtual void displayOn();
                virtual void displayOff();
};

#endif

#endif

