#ifndef __DEVICE_MICROCONTROLLER_RP2040_H__
#define __DEVICE_MICROCONTROLLER_RP2040_H__

#ifdef ARDUINO_ARCH_RP2040

#include <pico/mutex.h>
#include <etl/string.h>
#include <etl/map.h>

#include "device/microcontroller/microcontroller.h"


typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, recursive_mutex_t, 4> MutexMap;
class TwoWire;


class Microcontroller : AbstractMicrocontroller {
	private:
		MutexMap mutex_map;
	public:
		Microcontroller() {};
		virtual void start(uint32_t& timestamp, bool& booting);
		virtual void reset(uint32_t timestamp, bool rebooting);
		virtual void halt();
		void reset_uf2();

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

