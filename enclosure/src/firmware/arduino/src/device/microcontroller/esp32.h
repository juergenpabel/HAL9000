#ifndef __DEVICE_MICROCONTROLLER_ESP32_H__
#define __DEVICE_MICROCONTROLLER_ESP32_H__
#ifdef ARDUINO_ARCH_ESP32

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <etl/string.h>
#include <etl/map.h>

typedef struct {
	SemaphoreHandle_t  handle;
	StaticSemaphore_t  data;
} Semaphore;


typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, Semaphore, 4> MutexMap;
class TwoWire;


class Microcontroller {
	private:
		MutexMap     mutex_map;
	public:
		Microcontroller() {};

		virtual void start(uint32_t& timestamp, bool& booting);
		virtual void reset(uint32_t timestamp, bool rebooting);
		virtual void halt();

		virtual bool thread_create(void (*function)(), uint8_t core);

		virtual bool mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_exit(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_destroy(const etl::string<GLOBAL_KEY_SIZE>& name);

		virtual TwoWire* twowire_get(uint8_t instance, uint8_t pin_sda, uint8_t pin_scl);
};

#endif

#endif

