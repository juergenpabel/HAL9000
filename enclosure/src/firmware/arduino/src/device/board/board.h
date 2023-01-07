#ifndef __DEVICE_BOARD_BOARD_H__
#define __DEVICE_BOARD_BOARD_H__

#include <etl/string.h>
#include <ArduinoJson.h>


class AbstractBoard {
	protected:
		etl::string<GLOBAL_KEY_SIZE> m_identifier;
	public:
		AbstractBoard(const etl::string<GLOBAL_KEY_SIZE>& identifier) { this->m_identifier = identifier; };
		const etl::string<GLOBAL_KEY_SIZE>& getIdentifier() { return this->m_identifier; };

		virtual void start(bool& host_booting);
		virtual bool configure(const JsonVariant& configuration) = 0;
		virtual void reset(bool host_rebooting);
		virtual void halt();

		virtual void displayOn() = 0;
		virtual void displayOff() = 0;

		virtual void webserial_execute(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) = 0;
};

#endif

