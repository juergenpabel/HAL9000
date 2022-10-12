#include <TimeLib.h>
#include "system/settings.h"
#include "globals.h"


#define QUOTE(value) #value
#define STRING(value) QUOTE(value)

Runtime::Runtime() {
	(*this)["system/state:app/target"] = "booting";
}


bool Runtime::isAwake() {
	if(this->count("system/state:conciousness") == 0) {
		return true;
	}
	return (*this)["system/state:conciousness"].compare("awake")==0;
}


bool Runtime::isAsleep() {
	if(this->count("system/state:conciousness") != 1) {
		return false;
	}
	return (*this)["system/state:conciousness"].compare("asleep")==0;
}


void Runtime::update() {
	if(year() > 2001) {
		if((g_system_settings.find("system/state:time/sleep") != g_system_settings.end()) &&
		   (g_system_settings.find("system/state:time/wakeup") != g_system_settings.end())) {
			etl::string<GLOBAL_VALUE_SIZE> time_sleep;
			etl::string<GLOBAL_VALUE_SIZE> time_wakeup;

			time_sleep = g_system_settings["system/state:time/sleep"];
			time_wakeup = g_system_settings["system/state:time/wakeup"];
			if((time_sleep.length() >= 5) && (time_wakeup.length() >= 5)) {
				static etl::string<16> status_prev("awake");
				       etl::string<16> status_next("awake");
				       char            time_buffer[9] = "00:00:00";
				       etl::string<9>  time_now;

				time_buffer[0] += hour()/10;
				time_buffer[1] += hour()%10;
				time_buffer[3] += minute()/10;
				time_buffer[4] += minute()%10;
				time_buffer[6] += second()/10;
				time_buffer[7] += second()%10;
				time_now = time_buffer;
				if((time_sleep.compare(time_wakeup) < 0) && ((time_now.compare(time_sleep) >= 0) && (time_now.compare(time_wakeup) <= 0))) {
					status_next = "asleep";
				}
				if((time_sleep.compare(time_wakeup) > 0) && ((time_now.compare(time_sleep) >= 0) || (time_now.compare(time_wakeup) <= 0))) {
					status_next = "asleep";
				}
				if(status_prev != status_next) {
					(*this)["system/state:conciousness"] = status_next;
					status_prev = status_next;
					g_util_webserial.send("syslog/info", etl::string<UTIL_WEBSERIAL_BODY_SIZE>("Runtime::update() changing state to '").append(status_next).append("'"));
					if(this->isAwake()) {
						g_device_board.displayOn();
					} else {
						g_device_board.displayOff();
					}
				}
			}
		}
	}
}



size_t RuntimeWriter::write(uint8_t c) {
	this->m_runtime[m_key].append(1, (char)c);
	return 1;
}


size_t RuntimeWriter::write(const uint8_t *buffer, size_t length) {
	this->m_runtime[m_key].append((const char*)buffer, length);
	return length;
}

