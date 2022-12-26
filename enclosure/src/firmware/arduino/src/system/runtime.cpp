#include <TimeLib.h>
#include "system/settings.h"
#include "globals.h"


#define QUOTE(value) #value
#define STRING(value) QUOTE(value)

const etl::string<GLOBAL_VALUE_SIZE> Runtime::Null;


Runtime::Runtime() {
	this->m_status = StatusBooting;
	this->m_condition = ConditionAwake;
}


uint8_t Runtime::update() {
	if(this->m_status == StatusOnline && year() > 2001) {
		if((g_system_settings.find("runtime/condition:time-sleep") != g_system_settings.end())
		&& (g_system_settings.find("runtime/condition:time-wakeup") != g_system_settings.end())) {
			static etl::string<GLOBAL_VALUE_SIZE> time_sleep;
			static etl::string<GLOBAL_VALUE_SIZE> time_wakeup;
			       etl::string<9>                 time_now("00:00:00");

			time_sleep  = g_system_settings["runtime/condition:time-sleep"];
			time_wakeup = g_system_settings["runtime/condition:time-wakeup"];
			if((time_sleep.length() >= 5) && (time_wakeup.length() >= 5)) {
				Condition condition_now = ConditionUnknown;
				Condition condition_new = ConditionUnknown;

				condition_now = this->getCondition();
				time_now[0] += hour()/10;
				time_now[1] += hour()%10;
				time_now[3] += minute()/10;
				time_now[4] += minute()%10;
				time_now[6] += second()/10;
				time_now[7] += second()%10;
				if(((time_wakeup.compare(time_sleep) < 0) && ((time_now.compare(time_wakeup) >= 0) && (time_now.compare(time_sleep) <= 0)))
				|| ((time_wakeup.compare(time_sleep) > 0) && ((time_now.compare(time_wakeup) >= 0) || (time_now.compare(time_sleep) <= 0)))) {
					condition_new = ConditionAwake;
				}
				if(((time_sleep.compare(time_wakeup) < 0) && ((time_now.compare(time_sleep) >= 0) && (time_now.compare(time_wakeup) <= 0)))
				|| ((time_sleep.compare(time_wakeup) > 0) && ((time_now.compare(time_sleep) >= 0) || (time_now.compare(time_wakeup) <= 0)))) {
					condition_new = ConditionAsleep;
				}
				if(condition_new != ConditionUnknown && condition_now != condition_new) {
					if(condition_new == ConditionAwake) {
						g_util_webserial.send("syslog/info", etl::string<UTIL_WEBSERIAL_DATA_SIZE>("Runtime::update() changing state to 'awake'"));
						g_device_board.displayOn();
					}
					if(condition_new == ConditionAsleep) {
						g_util_webserial.send("syslog/info", etl::string<UTIL_WEBSERIAL_DATA_SIZE>("Runtime::update() changing state to 'asleep'"));
						g_device_board.displayOff();
					}
					this->setCondition(condition_new);
					condition_now = condition_new;
				}
			}
		}
	}
	return (this->m_status | this->m_condition);
}


const etl::string<GLOBAL_VALUE_SIZE>& Runtime::get(const etl::string<GLOBAL_KEY_SIZE>& key) {
	RuntimeMap::iterator item;

	item = this->m_map.find(key);
	if(item == this->m_map.end()) {
		return Runtime::Null;
	}
	return item->second;
}


void Runtime::set(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value) {
	RuntimeMap::iterator item;

	item = this->m_map.find(key);
	if(item == this->m_map.end()) {
		this->m_map.insert({key, value});
	} else {
		item->second = value;
	}
}


etl::string<GLOBAL_VALUE_SIZE>& Runtime::operator[](const etl::string<GLOBAL_KEY_SIZE>& key) {
	RuntimeMap::iterator item;

	item = this->m_map.find(key);
	if(item == this->m_map.end()) {
		this->m_map[key] = Runtime::Null;
		item = this->m_map.find(key);
	}
	return item->second;
}


bool Runtime::exists(const etl::string<GLOBAL_KEY_SIZE>& key) {
	return this->m_map.find(key) != this->m_map.end();
}


size_t RuntimeWriter::write(uint8_t c) {
	this->m_runtime[m_key].append(1, (char)c);
	return 1;
}


size_t RuntimeWriter::write(const uint8_t *buffer, size_t length) {
	this->m_runtime[m_key].append((const char*)buffer, length);
	return length;
}

