#include <TimeLib.h>
#include <ArduinoJson.h>
#include <etl/to_string.h>

#include "device/microcontroller/include.h"
#include "application/application.h"
#include "globals.h"


static const char* APPLICATION_STATUS[] = {
	"unknown",
	"booting",
	"configuring",
	"running",
	"resetting",
	"rebooting",
	"halting",
};


void on_application_runtime(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	if(data.containsKey("status") == true) {
		static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

		json["status"] = APPLICATION_STATUS[g_application.getStatus()];
		g_util_webserial.send("application/runtime", json);
	}
	if(data.containsKey("condition") == true) {
		etl::string<GLOBAL_VALUE_SIZE> awake("awake");
		etl::string<GLOBAL_VALUE_SIZE> asleep("asleep");

		if(awake.compare(data["condition"].as<const char*>()) == 0) {
			g_application.setCondition(ConditionAwake);
			g_device_board.displayOn();
			g_util_webserial.send("syslog/debug", "application/runtime#condition => OK");
		}
		if(asleep.compare(data["condition"].as<const char*>()) == 0) {
			g_application.setCondition(ConditionAsleep);
			g_device_board.displayOff();
			g_util_webserial.send("syslog/debug", "application/runtime#condition => OK");
		}
	}
	if(data.containsKey("time") == true) {
		if(data["time"].containsKey("epoch") == true) {
			long timestamp = 0;

			timestamp = data["time"]["epoch"].as<long>();
			if(timestamp <= 1009843199 /*2001-12-31 23:59:59*/) {
				g_util_webserial.send("syslog/error", "application/runtime#time => invalid epoch timestamp");
				return;
			}
			setTime(timestamp);
			g_util_webserial.send("syslog/debug", "application/runtime#time => OK");
		}
	}
	if(data.containsKey("shutdown") == true) {
		if(data["shutdown"].containsKey("target") == true) {
			etl::string<10> poweroff("poweroff");
			etl::string<10> reboot("reboot");

			if(poweroff.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_util_webserial.send("syslog/debug", "application/runtime#shutdown=poweroff");
				g_application.setStatus(StatusHalting);
			}
			if(reboot.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_util_webserial.send("syslog/debug", "application/runtime#shutdown=reboot");
				g_application.setStatus(StatusRebooting);
			}
		}
	}
}


void on_application_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	if(data.containsKey("list") == true) {
		static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

		json.clear();
		for(EnvironmentMap::iterator iter=g_application.m_environment.begin(); iter!=g_application.m_environment.end(); ++iter) {
			json[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("application/environment#list", json.as<JsonVariant>());
	}
	if(data.containsKey("get") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;

		key = data["env"]["key"].as<const char*>();
		if(key.length() > 0) {
			g_util_webserial.send("application/environment#get", g_application.getEnv(key));
			g_util_webserial.send("syslog/debug", "application/environment#get => OK");
		} else {
			g_util_webserial.send("syslog/debug", "application/environment#get => ERROR");
		}
	}
	if(data.containsKey("set") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = data["env"]["key"].as<const char*>();
		value = data["env"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_application.setEnv(key, value);
			g_util_webserial.send("syslog/debug", "application/application#env => OK");
		} else {
			g_util_webserial.send("syslog/debug", "application/application#env => ERROR");
		}
	}
}


void on_application_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

	if(data.containsKey("list") == true) {
		json.clear();

		for(SettingsMap::iterator iter=g_application.m_settings.begin(); iter!=g_application.m_settings.end(); ++iter) {
			json[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("application/settings#list", json);
	}
	if(data.containsKey("get") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;

		json.clear();
		key = data["get"]["key"].as<const char*>();
		if(key.length() > 0) {
			if(g_application.m_settings.count(key) == 1) {
				json["key"] = key.c_str();
				json["value"] = g_application.m_settings[key].c_str();
			}
			g_util_webserial.send("application/settings#get", json);
			g_util_webserial.send("syslog/debug", "application/settings#get => OK");
		} else {
			g_util_webserial.send("syslog/debug", "application/settings#get => ERROR");
		}
	}
	if(data.containsKey("set") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = data["set"]["key"].as<const char*>();
		value = data["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_application.m_settings[key] = value;
			g_util_webserial.send("syslog/debug", "application/settings#set => OK");
		} else {
			g_util_webserial.send("syslog/debug", "application/settings#set => ERROR");
		}
	}
	if(data.containsKey("load") == true) {
		if(g_application.m_settings.load() == true) {
			g_util_webserial.send("syslog/debug", "application/settings#load => OK");
		} else {
			g_util_webserial.send("syslog/debug", "application/settings#load => ERROR");
		}
	}
	if(data.containsKey("save") == true) {
		if(g_application.m_settings.save() == true) {
			g_util_webserial.send("syslog/debug", "application/settings#save => OK");
		} else {
			g_util_webserial.send("syslog/debug", "application/settings#save => ERROR");
		}
	}
	if(data.containsKey("reset") == true) {
		if(g_application.m_settings.reset() == true) {
			g_util_webserial.send("syslog/debug", "application/settings#reset => OK");
		} else {
			g_util_webserial.send("syslog/debug", "application/settings#reset => ERROR");
		}
	}
}

