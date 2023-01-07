#ifndef __DEVICE_MICROCONTROLLER_RP2040_H__
#define __DEVICE_MICROCONTROLLER_RP2040_H__

#ifdef ARDUINO_ARCH_RP2040

#include <pico/mutex.h>
#include <etl/string.h>
#include <etl/map.h>
#include <Wire.h>

#include "device/microcontroller/microcontroller.h"


typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, recursive_mutex_t, 4> MutexMap;


class Microcontroller : public AbstractMicrocontroller {
        protected:
		MutexMap  mutex_map;
		bool      twowire_init[2];
		TwoWire   twowire_data[2];
	public:
		Microcontroller();
		virtual void start(uint32_t& timestamp, bool& booting);
		virtual bool configure(const JsonVariant& configuration);
		virtual void reset(uint32_t timestamp, bool rebooting);
		virtual void halt();
		void reset_uf2();

		virtual bool thread_create(void (*function)(), uint8_t core);

		virtual bool mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name, bool recursive);
		virtual bool mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_exit(const etl::string<GLOBAL_KEY_SIZE>& name);
		virtual bool mutex_destroy(const etl::string<GLOBAL_KEY_SIZE>& name);

		virtual TwoWire* twowire_get(uint8_t instance);
		virtual void     webserial_execute(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);

};

#endif

#endif

