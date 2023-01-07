#ifndef __DEVICE_BOARD_ROUNDYPI_H__
#define __DEVICE_BOARD_ROUNDYPI_H__

#ifdef ARDUINO_ROUNDYPI

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

		virtual void webserial_execute(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
};

#endif

#endif

