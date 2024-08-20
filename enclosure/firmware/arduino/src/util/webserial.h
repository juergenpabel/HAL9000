#ifndef __ROUNDYPI_UTIL_WEBSERIAL_H__
#define __ROUNDYPI_UTIL_WEBSERIAL_H__

#include <etl/string.h>
#include <etl/map.h>
#include <etl/queue_lockable.h>

#include "gui/gui.h"
#include "device/microcontroller/include.h"
extern Microcontroller g_device_microcontroller;


#define WEBSERIAL_LINE_SIZE (2+GLOBAL_KEY_SIZE+4+GLOBAL_VALUE_SIZE+2)
typedef void (*webserial_command_func)(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);


template<const size_t VSize> class WebSerialQueue : public etl::queue_lockable<etl::string<WEBSERIAL_LINE_SIZE>, VSize, etl::memory_model::MEMORY_MODEL_SMALL> {
	private:
		const etl::string<GLOBAL_KEY_SIZE> mutex_name;
	public:
		WebSerialQueue(const etl::string<GLOBAL_KEY_SIZE> name) : mutex_name(name) { g_device_microcontroller.mutex_create(this->mutex_name, true); };
	protected:
		virtual void   lock() const { g_device_microcontroller.mutex_enter(this->mutex_name); };
		virtual void unlock() const { g_device_microcontroller.mutex_leave(this->mutex_name); };
};


class WebSerial {
	private:
		etl::map<etl::string<GLOBAL_KEY_SIZE>, webserial_command_func, UTIL_WEBSERIAL_COMMANDS_MAX> commands;
		WebSerialQueue<UTIL_WEBSERIAL_QUEUE_RECV_MAX> queue_recv;
		WebSerialQueue<UTIL_WEBSERIAL_QUEUE_SEND_MAX> queue_send;
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

