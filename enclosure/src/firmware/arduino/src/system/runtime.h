#ifndef __ROUNDYPI_SYSTEM_RUNTIME_H__
#define __ROUNDYPI_SYSTEM_RUNTIME_H__

#include <etl/string.h>
#include <etl/map.h>


class Runtime : public etl::map<etl::string<GLOBAL_KEY_SIZE>, etl::string<GLOBAL_VALUE_SIZE>, SYSTEM_RUNTIME_MAX> {
	public:
		Runtime();
		bool  isAwake();
		bool  isAsleep();
		void  update();
};


class RuntimeWriter {
	private:
		Runtime& m_runtime;
		etl::string<GLOBAL_KEY_SIZE> m_key;
	public:
		RuntimeWriter(Runtime& runtime, const etl::string<GLOBAL_KEY_SIZE>& key) : m_runtime(runtime), m_key(key) { this->m_runtime[m_key.c_str()] = ""; };

		size_t write(uint8_t c);
		size_t write(const uint8_t *buffer, size_t length);
};

#endif

