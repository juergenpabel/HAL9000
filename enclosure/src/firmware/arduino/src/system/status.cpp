#include <TimeLib.h>
#include "system/status.h"

Status::Status() {
	(*this)["system/state:conciousness"] = "awake";
}


bool Status::isAwake() {
	return (*this)["system/state:conciousness"] == std::string("awake");
}


bool Status::isAsleep() {
	return (*this)["system/state:conciousness"] == std::string("asleep");
}


void Status::update() {
	static std::string status;

	if(year() > 2001) {
		uint8_t  sleep_hour, sleep_minute;
		uint8_t  wakeup_hour, wakeup_minute;

		if(sleep_hour*60+sleep_minute > wakeup_hour*60+wakeup_minute) {
			wakeup_hour += 24;
		}
		if((hour()*60+minute() > sleep_hour*60+sleep_minute) && (hour()*60+minute() < wakeup_hour*60+wakeup_minute)) {
			if(status != std::string("asleep")) {
				status = "asleep";
				(*this)["system/state:conciousness"] = status;
			}
		} else {
			if(status != std::string("awake") == false) {
				status = "awake";
				(*this)["system/state:conciousness"] = status;
			}
		}
	}
}

