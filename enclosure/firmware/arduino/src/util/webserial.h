#ifndef __UTIL_WEBSERIAL_H__
#define __UTIL_WEBSERIAL_H__

#include <etl/string.h>
#include <etl/map.h>
#include <etl/queue_lockable.h>
#include <TFT_eSPI.h>

#include "gui/gui.h"
#include "device/microcontroller/include.h"
extern Microcontroller g_device_microcontroller;


#define WEBSERIAL_LINE_SIZE (2+GLOBAL_KEY_SIZE+4+GLOBAL_VALUE_SIZE+2)
typedef void (*webserial_command_func)(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, webserial_command_func, UTIL_WEBSERIAL_COMMANDS_MAX> WebSerialCommandMap;


template<const size_t VSize> class WebSerialQueue : public etl::queue_lockable<etl::string<WEBSERIAL_LINE_SIZE>, VSize, etl::memory_model::MEMORY_MODEL_SMALL> {
	private:
		const etl::string<GLOBAL_KEY_SIZE> mutex_name;
	public:
		WebSerialQueue(const etl::string<GLOBAL_KEY_SIZE> name);
	protected:
		virtual void   lock() const;
		virtual void unlock() const;
};
typedef WebSerialQueue<UTIL_WEBSERIAL_QUEUE_RECV_MAX> WebSerialRecvQueue;
typedef WebSerialQueue<UTIL_WEBSERIAL_QUEUE_SEND_MAX> WebSerialSendQueue;


class WebSerial {
	private:
		WebSerialCommandMap  commands;
		WebSerialRecvQueue   queue_recv;
		WebSerialSendQueue   queue_send;
		unsigned long        millis_heartbeatRX;
		unsigned long        millis_heartbeatTX;

		void heartbeat();
		bool isAlive();
	protected:
		void handle(const etl::string<WEBSERIAL_LINE_SIZE>& line);
		void handle(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	public:
		WebSerial();
		void begin();
		void update();

		void send(const etl::string<GLOBAL_KEY_SIZE>& command, const etl::string<GLOBAL_VALUE_SIZE>& data, bool data_stringify = true, bool priority = false);
		void send(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data, bool priority = false);

		bool addCommand(const etl::string<GLOBAL_KEY_SIZE>& command, webserial_command_func handler);
		bool delCommand(const etl::string<GLOBAL_KEY_SIZE>& command, webserial_command_func handler);
		bool hasCommand(const etl::string<GLOBAL_KEY_SIZE>& command);
		void clearCommands();

	friend class Application;
	friend unsigned long gui_screen_animations(unsigned long validity, TFT_eSPI* gui);
};

#endif

