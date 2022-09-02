#include <string>
#include <TimeLib.h>
#include "system/settings.h"
#include "globals.h"


#define QUOTE(value) #value
#define STRING(value) QUOTE(value)


Runtime::Runtime() {
	(*this)["system/state:conciousness"] = std::string("awake");
}


bool Runtime::isAwake() {
	if(this->count("system/state:conciousness") != 1) {
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
			std::string time_sleep;
			std::string time_wakeup;

			time_sleep = g_system_settings["system/state:time/sleep"];
			time_wakeup = g_system_settings["system/state:time/wakeup"];
			if((time_sleep.length() >= 5) && (time_wakeup.length() >= 5)) {
				static std::string status_prev("awake");
				       std::string status_next("awake");
				       char        time_buffer[9] = "00:00:00";
				       std::string time_now;

				time_buffer[0] += hour()/10;
				time_buffer[1] += hour()%10;
				time_buffer[3] += minute()/10;
				time_buffer[4] += minute()%10;
				time_buffer[6] += second()/10;
				time_buffer[7] += second()%10;
				time_now = time_buffer;
				if((time_sleep.compare(time_wakeup) < 0) && ((time_now.compare(time_sleep) >= 0) && (time_now.compare(time_wakeup) <= 0))) {
					status_next = std::string("asleep");
				}
				if((time_sleep.compare(time_wakeup) > 0) && ((time_now.compare(time_sleep) >= 0) || (time_now.compare(time_wakeup) <= 0))) {
					status_next = std::string("asleep");
				}
				if(status_prev != status_next) {
					(*this)["system/state:conciousness"] = status_next;
					status_prev = status_next;
					g_util_webserial.send("syslog", arduino::String("Runtime::update() changing state to '")+status_next.c_str()+"'");
				}
			}
		}
	}
}

