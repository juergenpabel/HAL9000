#ifndef __DEVICE_BOARD_ROUNDYPI_H__
#define __DEVICE_BOARD_ROUNDYPI_H__

#ifdef ARDUINO_SBCOMPONENTS_ROUNDYPI

#include <FreeRTOS.h>
#include <queue.h>
#include "device/board/board.h"


class Board : public AbstractBoard {
	public:
		Board();
		virtual void start(bool& host_booting);
		virtual bool configure(const JsonVariant& configuration);
		virtual void reset(bool host_rebooting);
		virtual void halt();

		virtual void displayOn();
                virtual void displayOff();
};

#endif

#endif

