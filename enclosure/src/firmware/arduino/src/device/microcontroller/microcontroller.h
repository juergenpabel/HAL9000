#ifndef __DEVICE_MICROCONTROLLER_MICROCONTROLLER_H__
#define __DEVICE_MICROCONTROLLER_MICROCONTROLLER_H__

#include <etl/string.h>

class TwoWire;


class AbstractMicrocontroller {
	public:
		AbstractMicrocontroller() {};

		virtual void start(uint32_t& timestamp, bool& booting) = 0;
		virtual void reset(uint32_t timestamp, bool rebooting) = 0;
		virtual void halt() = 0;

		virtual bool thread_create(void (*function)(), uint8_t core) = 0;

		virtual bool mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name, bool recursive) = 0;
		virtual bool mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;
		virtual bool mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;
		virtual bool mutex_exit(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;
		virtual bool mutex_destroy(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;

		virtual TwoWire* twowire_get(uint8_t instance, uint8_t pin_sda, uint8_t pin_scl) = 0;
};

#endif

