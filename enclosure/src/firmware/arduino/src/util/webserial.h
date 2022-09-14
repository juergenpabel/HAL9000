#ifndef __ROUNDYPI_UTIL_WEBSERIAL_H__
#define __ROUNDYPI_UTIL_WEBSERIAL_H__

#include <etl/string.h>
#include <etl/queue.h>
#include <etl/map.h>


typedef void (*webserial_command_func)(const JsonVariant& data);


class WebSerial {
	private:
		recursive_mutex_t serial_mutex;

		etl::map<etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>, webserial_command_func, UTIL_WEBSERIAL_COMMANDS_MAX> commands;
		etl::queue<etl::string<UTIL_WEBSERIAL_LINE_SIZE>, UTIL_WEBSERIAL_QUEUE_RECV_MAX> queue_recv;
		etl::queue<etl::string<UTIL_WEBSERIAL_LINE_SIZE>, UTIL_WEBSERIAL_QUEUE_SEND_MAX> queue_send;
	public:
		WebSerial();
		void update();
		void set(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, webserial_command_func handler);
		void send(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, const JsonVariant& data);
		void send(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, const etl::string<UTIL_WEBSERIAL_BODY_SIZE>& data);
};

#endif

