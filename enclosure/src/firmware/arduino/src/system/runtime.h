#ifndef __ROUNDYPI_SYSTEM_RUNTIME_H__
#define __ROUNDYPI_SYSTEM_RUNTIME_H__

#include <etl/string.h>
#include <etl/map.h>
#include <ArduinoJson.h>


typedef enum {
	StatusUnknown   = 0x00,
	StatusPowerOn   = 0x01,
	StatusBooting   = 0x02,
	StatusOffline   = 0x03,
	StatusOnline    = 0x04,
	StatusResetting = 0x05,
	StatusRebooting = 0x06,
	StatusHalting   = 0x07,
	StatusMask      = 0x0f,
	StatusUnchanged = 0xff,
} Status;

typedef enum {
	ConditionUnknown = 0x80,
	ConditionAsleep  = 0x90,
	ConditionAwake   = 0xa0,
	ConditionMask    = 0xf0
} Condition;

typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, etl::string<GLOBAL_VALUE_SIZE>, SYSTEM_RUNTIME_MAX> RuntimeMap;


class Runtime {
	protected:
		RuntimeMap m_map;
		Status     m_status;
		Condition  m_condition;

	public:
		Runtime();
		uint8_t    update();

		void       setCondition(Condition condition) { this->m_condition = condition; };
		Condition  getCondition() { return this->m_condition; };

		void       setStatus(Status status) { if(status != StatusUnchanged) { this->m_status = status; } };
		Status     getStatus() { return this->m_status; };

		const etl::string<GLOBAL_VALUE_SIZE>& get(const etl::string<GLOBAL_KEY_SIZE>& key);
		void                                  set(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value);

		etl::string<GLOBAL_VALUE_SIZE>&       operator[](const etl::string<GLOBAL_KEY_SIZE>& key);

		bool                                  exists(const etl::string<GLOBAL_KEY_SIZE>& key);

	friend class RuntimeWriter;
	friend void on_system_runtime(const JsonVariant& data);
	static const etl::string<GLOBAL_VALUE_SIZE> Null;
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

