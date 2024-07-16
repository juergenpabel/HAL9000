#ifndef __ROUNDYPI_UTIL_WEBSERIAL_H__
#define __ROUNDYPI_UTIL_WEBSERIAL_H__

#include <etl/string.h>
#include <etl/queue.h>
#include <etl/map.h>


typedef void (*webserial_command_func)(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);


class WebSerial {
	private:
		etl::map<etl::string<GLOBAL_KEY_SIZE>, webserial_command_func, UTIL_WEBSERIAL_COMMANDS_MAX> commands;
		etl::queue<etl::string<GLOBAL_VALUE_SIZE>, UTIL_WEBSERIAL_QUEUE_RECV_MAX> queue_recv;
		etl::queue<etl::string<GLOBAL_VALUE_SIZE>, UTIL_WEBSERIAL_QUEUE_SEND_MAX> queue_send;
	protected:
		void handle(const etl::string<GLOBAL_VALUE_SIZE>& line);
		void handle(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	public:
		WebSerial();
		void begin();
		void update();
		void setCommand(const etl::string<GLOBAL_KEY_SIZE>& command, webserial_command_func handler);
		void send(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
		void send(const etl::string<GLOBAL_KEY_SIZE>& command, const etl::string<GLOBAL_VALUE_SIZE>& data, bool data_stringify = true);

	friend class Application;
	friend void gui_screen_animations(bool refresh);
};

#endif

