#ifndef __DEVICE_BOARD_BOARD_H__
#define __DEVICE_BOARD_BOARD_H__


class AbstractBoard {
	public:
		AbstractBoard();
		virtual void start(bool& host_booting);
		virtual void reset(bool host_rebooting);
		virtual void halt();

		virtual void displayOn() = 0;
		virtual void displayOff() = 0;
};

#endif

