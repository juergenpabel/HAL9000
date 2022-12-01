#include <TimeLib.h>
#include <ArduinoJson.h>
#include <etl/to_string.h>
#include "device/microcontroller/include.h"
#include "system/system.h"
#include "system/time.h"
#include "system/webserial.h"
#include "globals.h"


void on_system_app(const JsonVariant& data) {
	if(data.containsKey("shutdown")) {
		if(data["shutdown"].containsKey("target")) {
			etl::string<10> poweroff("poweroff");
			etl::string<10> reboot("reboot");

			if(poweroff.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_util_webserial.send("syslog/debug", "system/app#target=poweroff");
				g_system_runtime["system/state:app/target"] = "halting";
			}
			if(reboot.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_util_webserial.send("syslog/debug", "system/app#target=reboot");
				g_system_runtime["system/state:app/target"] = "rebooting";
			}
			g_device_microcontroller.mutex_enter("Serial");
			Serial.flush();
			Serial.end();
			g_device_microcontroller.mutex_exit("Serial");
		}
	}
}


void on_system_mcu(const JsonVariant& data) {
	if(data.containsKey("reset")) {
		g_util_webserial.send("syslog/debug", "system/mcu#reset");
		g_device_microcontroller.reset(now(), false);
	}
	if(data.containsKey("halt")) {
		g_util_webserial.send("syslog/debug", "system/mcu#halt");
		g_device_microcontroller.halt();
	}
}


void on_system_runtime(const JsonVariant& data) {
	static StaticJsonDocument<1024> result;

	result.clear();
	if(data.containsKey("list")) {
		for(Runtime::iterator iter=g_system_runtime.begin(); iter!=g_system_runtime.end(); ++iter) {
			result[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("system/runtime#list", result.as<JsonVariant>());
	}
	if(data.containsKey("set")) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = data["set"]["key"].as<const char*>();
		value = data["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_system_runtime[key.c_str()] = value.c_str();
			g_util_webserial.send("syslog/debug", "system/runtime#set => OK");
		} else {
			g_util_webserial.send("syslog/debug", "system/runtime#set => ERROR");
		}
	}
}


void on_system_settings(const JsonVariant& data) {
	static StaticJsonDocument<1024> result;

	result.clear();
	if(data.containsKey("list")) {

		for(Settings::iterator iter=g_system_settings.begin(); iter!=g_system_settings.end(); ++iter) {
			result[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("system/settings#list", result);
	}
	if(data.containsKey("get")) {
		etl::string<GLOBAL_KEY_SIZE> key;

		key = data["get"]["key"].as<const char*>();
		if(key.length() > 0) {
			if(g_system_settings.count(key) == 1) {
				result["key"] = key.c_str();
				result["value"] = g_system_settings[key].c_str();
			}
			g_util_webserial.send("system/settings#get", result);
			g_util_webserial.send("syslog/debug", "system/settings#get => OK");
		} else {
			g_util_webserial.send("syslog/debug", "system/settings#get => ERROR");
		}
	}
	if(data.containsKey("set")) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = data["set"]["key"].as<const char*>();
		value = data["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_system_settings[key] = value;
			g_util_webserial.send("syslog/debug", "system/settings#set => OK");
		} else {
			g_util_webserial.send("syslog/debug", "system/settings#set => ERROR");
		}
	}
	if(data.containsKey("load")) {
		if(g_system_settings.load() == true) {
			g_util_webserial.send("syslog/debug", "system/settings#load => OK");
		} else {
			g_util_webserial.send("syslog/debug", "system/settings#load => ERROR");
		}
	}
	if(data.containsKey("save")) {
		if(g_system_settings.save() == true) {
			g_util_webserial.send("syslog/debug", "system/settings#save => OK");
		} else {
			g_util_webserial.send("syslog/debug", "system/settings#save => ERROR");
		}
	}
	if(data.containsKey("reset")) {
		if(g_system_settings.reset() == true) {
			g_util_webserial.send("syslog/debug", "system/settings#reset => OK");
		} else {
			g_util_webserial.send("syslog/debug", "system/settings#reset => ERROR");
		}
	}
}


void on_system_time(const JsonVariant& data) {
	if(data.containsKey("sync")) {
		if(data["sync"].containsKey("epoch")) {
			system_time_set(data["sync"]["epoch"].as<long>());
		}
	}
	if(data.containsKey("config")) {
		if(data["config"].containsKey("epoch")) {
			time_t epoch = 0;

			epoch = data["config"]["epoch"].as<unsigned long>();
			if(epoch > 0) {
				setTime(epoch);
			}
		}
		if(data["config"].containsKey("interval")) {
			int interval_secs = data["config"]["interval"].as<int>();
			etl::to_string(interval_secs, g_system_runtime["system/time:sync/interval"]);
			if(interval_secs > 0) {
				setSyncProvider(system_time_sync);
				setSyncInterval(interval_secs);
			}
		}
	}
}


void on_system_reset(const JsonVariant& data) {
	g_util_webserial.send("syslog/info", "Resetting system...");
	system_reset();
}

