#ifndef __DEVICE_MICROCONTROLLER_MICROCONTROLLER_H__
#define __DEVICE_MICROCONTROLLER_MICROCONTROLLER_H__

#include <etl/string.h>
#include <ArduinoJson.h>

class TwoWire;


class AbstractMicrocontroller {
	protected:
		etl::string<GLOBAL_KEY_SIZE> m_identifier;
	public:
		AbstractMicrocontroller(const etl::string<GLOBAL_KEY_SIZE>& identifier) { this->m_identifier = identifier; };
		const etl::string<GLOBAL_KEY_SIZE>& getIdentifier() { return this->m_identifier; };

		virtual void start(uint32_t& timestamp, bool& booting) = 0;
		virtual bool configure(const JsonVariant& configuration) = 0;
		virtual void reset(uint32_t timestamp, bool rebooting) = 0;
		virtual void halt() = 0;

		virtual bool task_create(const etl::string<GLOBAL_KEY_SIZE>& task_name, void (*task_function)(), uint8_t core) = 0;

		virtual bool mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name, bool recursive) = 0;
		virtual bool mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;
		virtual bool mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;
		virtual bool mutex_exit(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;
		virtual bool mutex_destroy(const etl::string<GLOBAL_KEY_SIZE>& name) = 0;

		virtual TwoWire* twowire_get(uint8_t instance) = 0;
};

#endif

