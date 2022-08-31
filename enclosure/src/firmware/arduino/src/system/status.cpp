#include <string>
#include <TimeLib.h>
#include "system/settings.h"
#include "globals.h"


#define QUOTE(value) #value
#define STRING(value) QUOTE(value)


Status::Status() {
	(*this)["system/state:conciousness"] = std::string("awake");
	(*this)["system/time:sync/interval"] = STRING(SYSTEM_STATUS_TIME_SYNC_INTERVAL);
	(*this)["gui/screen:volume/level"] = STRING(SYSTEM_STATUS_VOLUME);
	(*this)["gui/screen:volume/mute"] = STRING(SYSTEM_STATUS_MUTE);
}


bool Status::isAwake() {
	return (*this)["system/state:conciousness"] == std::string("awake");
}


bool Status::isAsleep() {
	return (*this)["system/state:conciousness"] == std::string("asleep");
}


void Status::update() {
	if(year() > 2001) {
		std::string time_now;
		std::string time_sleep;
		std::string time_wakeup;

		time_now = std::string("00:00");
		time_now[0] += hour()/10;
		time_now[1] += hour()%10;
		time_now[3] += minute()/10;
		time_now[4] += minute()%10;
		time_sleep = g_system_settings["system/state:time/sleep"];
		time_wakeup = g_system_settings["system/state:time/wakeup"];
		if((time_sleep.length() == 5) && (time_wakeup.length() == 5)) {
			static std::string status_previous = "awake";
			       std::string status_next;

			status_next = std::string("awake");
			if((time_sleep.compare(time_wakeup) < 0) && ((time_now.compare(time_sleep) >= 0) && (time_now.compare(time_wakeup) <= 0))) {
				status_next = std::string("asleep");
			}
			if((time_sleep.compare(time_wakeup) > 0) && ((time_now.compare(time_sleep) >= 0) || (time_now.compare(time_wakeup) <= 0))) {
				status_next = std::string("asleep");
			}
			if(status_previous != status_next) {
				(*this)["system/state:conciousness"] = status_next;
				status_previous = status_next;
			}
		}
	}
}

