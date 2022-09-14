#include <TimeLib.h>
#include <ArduinoJson.h>
#include <etl/to_string.h>
#include "system/webserial.h"
#include "system/rp2040.h"
#include "system/time.h"
#include "globals.h"


void on_system_runtime(const JsonVariant& parameter) {
	static StaticJsonDocument<1024> result;

	result.clear();
	if(parameter.containsKey("list")) {
		for(Runtime::iterator iter=g_system_runtime.begin(); iter!=g_system_runtime.end(); ++iter) {
			result[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("system/runtime#list", result.as<JsonVariant>());
	}
	if(parameter.containsKey("set")) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = parameter["set"]["key"].as<const char*>();
		value = parameter["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_system_runtime[key.c_str()] = value.c_str();
			g_util_webserial.send("syslog", "system/runtime#set => OK");
		} else {
			g_util_webserial.send("syslog", "system/runtime#set => ERROR");
		}
	}
}


void on_system_settings(const JsonVariant& parameter) {
	static StaticJsonDocument<1024> result;

	result.clear();
	if(parameter.containsKey("list")) {

		for(Settings::iterator iter=g_system_settings.begin(); iter!=g_system_settings.end(); ++iter) {
			result[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("system/settings#list", result);
	}
	if(parameter.containsKey("get")) {
		etl::string<GLOBAL_KEY_SIZE> key;

		key = parameter["get"]["key"].as<const char*>();
		if(key.length() > 0) {
			if(g_system_settings.count(key) == 1) {
				result["key"] = key.c_str();
				result["value"] = g_system_settings[key].c_str();
			}
			g_util_webserial.send("system/settings#get", result);
			g_util_webserial.send("syslog", "system/settings#get => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#get => ERROR");
		}
	}
	if(parameter.containsKey("set")) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = parameter["set"]["key"].as<const char*>();
		value = parameter["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_system_settings[key] = value;
			g_util_webserial.send("syslog", "system/settings#set => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#set => ERROR");
		}
	}
	if(parameter.containsKey("load")) {
		if(g_system_settings.load() == true) {
			g_util_webserial.send("syslog", "system/settings#load => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#load => ERROR");
		}
	}
	if(parameter.containsKey("save")) {
		if(g_system_settings.save() == true) {
			g_util_webserial.send("syslog", "system/settings#save => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#save => ERROR");
		}
	}
	if(parameter.containsKey("reset")) {
		if(g_system_settings.reset() == true) {
			g_util_webserial.send("syslog", "system/settings#reset => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#reset => ERROR");
		}
	}
}


void on_system_time(const JsonVariant& parameter) {
	if(parameter.containsKey("sync")) {
		if(parameter["sync"].containsKey("epoch")) {
			system_time_set(parameter["sync"]["epoch"].as<long>());
		}
	}
	if(parameter.containsKey("config")) {
		int interval_secs = SYSTEM_STATUS_TIME_SYNC_INTERVAL;

		if(g_system_runtime.count("system/time:sync/interval") == 1) {
			interval_secs = atoi(g_system_runtime["system/time:sync/interval"].c_str());
		}
		if(parameter["config"].containsKey("interval")) {
			interval_secs = parameter["config"]["interval"].as<int>();
			etl::to_string(interval_secs, g_system_runtime["system/time:sync/interval"]);
		}
		setSyncProvider(system_time_sync);
		setSyncInterval(interval_secs);
	}
}


void on_system_reset(const JsonVariant& parameter) {
	bool  uf2 = false;

	if(parameter.containsKey("uf2")) {
		uf2 = parameter["uf2"].as<bool>();
	}
	if(uf2) {
		g_util_webserial.send("syslog", "Resetting RP2040 with boot target UF2...");
		system_rp2040_reset_uf2();
	}
	g_util_webserial.send("syslog", "Resetting RP2040...");
	system_rp2040_reset();
}

