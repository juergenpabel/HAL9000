#ifndef __DEVICE_BOARD_BOARD_H__
#define __DEVICE_BOARD_BOARD_H__


class AbstractBoard {
	public:
		AbstractBoard() {};
		virtual void start(bool& host_booting) = 0;
		virtual void reset(uint32_t timestamp, bool host_rebooting) = 0;
		virtual void halt() = 0;

		virtual void displayOn() = 0;
		virtual void displayOff() = 0;
};

#endif

