#ifndef __ROUNDYPI_UTIL_WEBSERIAL_H__
#define __ROUNDYPI_UTIL_WEBSERIAL_H__

#include "gui/gui.h"
#include "device/board/include.h"
#include <etl/string.h>
#include <etl/map.h>


#define WEBSERIAL_LINE_SIZE (2+GLOBAL_KEY_SIZE+4+GLOBAL_VALUE_SIZE+2)
typedef void (*webserial_command_func)(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);

class WebSerial {
	private:
		etl::map<etl::string<GLOBAL_KEY_SIZE>, webserial_command_func, UTIL_WEBSERIAL_COMMANDS_MAX> commands;
		QueueHandle_t queue_recv_handle;
		StaticQueue_t queue_recv_metadata;
		uint8_t       queue_recv_itemdata[WEBSERIAL_LINE_SIZE * UTIL_WEBSERIAL_QUEUE_RECV_MAX];
		QueueHandle_t queue_send_handle;
		StaticQueue_t queue_send_metadata;
		uint8_t       queue_send_itemdata[WEBSERIAL_LINE_SIZE * UTIL_WEBSERIAL_QUEUE_SEND_MAX];
	protected:
		void handle(const etl::string<WEBSERIAL_LINE_SIZE>& line);
		void handle(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	public:
		WebSerial();
		void begin();
		void setCommand(const etl::string<GLOBAL_KEY_SIZE>& command, webserial_command_func handler);
		void update();
		void send(const etl::string<GLOBAL_KEY_SIZE>& command, const etl::string<GLOBAL_VALUE_SIZE>& data, bool data_stringify = true);
		void send(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);

	friend class Application;
	friend gui_refresh_t gui_screen_animations(bool refresh);
};

#endif

