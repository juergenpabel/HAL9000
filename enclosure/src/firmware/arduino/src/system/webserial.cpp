#include <string>
#include <TimeLib.h>
#include <JSONVar.h>
#include "system/webserial.h"
#include "system/rp2040.h"
#include "system/time.h"
#include "globals.h"


void on_system_runtime(JSONVar parameter) {
	if(parameter.hasOwnProperty("list")) {
		JSONVar result;

		for(Runtime::iterator iter=g_system_runtime.begin(); iter!=g_system_runtime.end(); ++iter) {
			result[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("system/runtime#list", result);
	}
	if(parameter.hasOwnProperty("set")) {
		std::string key;
		std::string value;

		key = (const char*)parameter["set"]["key"];
		value = (const char*)parameter["set"]["value"];
		if(key.length() > 0 && value.length() > 0) {
			g_system_runtime[key] = value;
			g_util_webserial.send("syslog", "system/runtime#set => OK");
		} else {
			g_util_webserial.send("syslog", "system/runtime#set => ERROR");
		}
	}
}


void on_system_settings(JSONVar parameter) {
	if(parameter.hasOwnProperty("list")) {
		JSONVar result;

		for(Settings::iterator iter=g_system_settings.begin(); iter!=g_system_settings.end(); ++iter) {
			result[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("system/settings#list", result);
	}
	if(parameter.hasOwnProperty("get")) {
		std::string key;

		key = (const char*)parameter["get"]["key"];
		if(key.length() > 0) {
			JSONVar data;

			if(g_system_settings.count(key) == 1) {
				data["key"] = key.c_str();
				data["value"] = g_system_settings[key].c_str();
			}
			g_util_webserial.send("system/settings#get", data);
			g_util_webserial.send("syslog", "system/settings#get => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#get => ERROR");
		}
	}
	if(parameter.hasOwnProperty("set")) {
		std::string key;
		std::string value;

		key = (const char*)parameter["set"]["key"];
		value = (const char*)parameter["set"]["value"];
		if(key.length() > 0 && value.length() > 0) {
			g_system_settings[key] = value;
			g_util_webserial.send("syslog", "system/settings#set => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#set => ERROR");
		}
	}
	if(parameter.hasOwnProperty("load")) {
		if(g_system_settings.load() == true) {
			g_util_webserial.send("syslog", "system/settings#load => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#load => ERROR");
		}
	}
	if(parameter.hasOwnProperty("save")) {
		if(g_system_settings.save() == true) {
			g_util_webserial.send("syslog", "system/settings#save => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#save => ERROR");
		}
	}
	if(parameter.hasOwnProperty("reset")) {
		if(g_system_settings.reset() == true) {
			g_util_webserial.send("syslog", "system/settings#reset => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#reset => ERROR");
		}
	}
}


void on_system_time(JSONVar parameter) {
	if(parameter.hasOwnProperty("sync")) {
		if(parameter["sync"].hasOwnProperty("epoch")) {
			system_time_set(parameter["sync"]["epoch"]);
		}
	}
	if(parameter.hasOwnProperty("config")) {
		int interval_secs = SYSTEM_STATUS_TIME_SYNC_INTERVAL;

		if(g_system_runtime.count("system/time:sync/interval") == 1) {
			interval_secs = std::stoi(g_system_runtime["system/time:sync/interval"]);
		}
		if(parameter["config"].hasOwnProperty("interval")) {
			interval_secs = parameter["config"]["interval"];
			g_system_runtime["system/time:sync/interval"] = std::to_string(interval_secs);
		}
		setSyncProvider(system_time_sync);
		setSyncInterval(interval_secs);
	}
}


void on_system_reset(JSONVar parameter) {
	bool  uf2 = false;

	if(parameter.hasOwnProperty("uf2")) {
		uf2 = parameter["uf2"];
	}
	if(uf2) {
		g_util_webserial.send("syslog", "Resetting RP2040 with boot target UF2...");
		system_rp2040_reset_uf2();
	}
	g_util_webserial.send("syslog", "Resetting RP2040...");
	system_rp2040_reset();
}

