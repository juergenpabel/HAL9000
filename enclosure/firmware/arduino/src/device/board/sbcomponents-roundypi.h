#ifndef __DEVICE_BOARD_ROUNDYPI_H__
#define __DEVICE_BOARD_ROUNDYPI_H__

#ifdef ARDUINO_SBCOMPONENTS_ROUNDYPI

#include "device/board/board.h"


class Board : public AbstractBoard {
	private:
		bool displayStatus;
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

