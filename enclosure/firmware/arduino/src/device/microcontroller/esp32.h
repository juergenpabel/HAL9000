#ifndef __DEVICE_MICROCONTROLLER_ESP32_H__
#define __DEVICE_MICROCONTROLLER_ESP32_H__

#ifdef ARDUINO_ARCH_ESP32
#include <esp_log.h>

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <etl/string.h>
#include <etl/map.h>
#include <Wire.h>

#include "application/application.h"
#include "microcontroller.h"

typedef struct {
	SemaphoreHandle_t  handle;
	StaticSemaphore_t  data;
} Semaphore;


typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, Semaphore, 16> MutexMap;


class Microcontroller : public AbstractMicrocontroller {
	private:
		static uint32_t       reset_timestamp;
		static vprintf_like_t original_vprintf;
	protected:
		MutexMap  mutex_map;
		bool      twowire_init[2];
		TwoWire   twowire_data[2];
	public:
		Microcontroller();

		virtual void start(uint32_t& timestamp);
		virtual bool configure(const JsonVariant& configuration);
		virtual void reset(uint32_t timestamp);
		virtual void halt();

		static int vprintf(const char* format, va_list message);

		virtual bool task_create(const etl::string<GLOBAL_KEY_SIZE>& task_name, void (*task_function)(), uint8_t core);

		virtual bool mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_leave(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_destroy(const etl::string<GLOBAL_KEY_SIZE>& name);

		virtual TwoWire* twowire_get(uint8_t instance);
};

#endif

#endif

