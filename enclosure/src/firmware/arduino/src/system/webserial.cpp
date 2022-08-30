#include <TimeLib.h>
#include <JSONVar.h>
#include "system/webserial.h"
#include "system/rp2040.h"
#include "globals.h"


void on_system_settings(JSONVar parameter) {
	if(parameter.hasOwnProperty("set")) {
		const char* key;
		const char* value;

		key = parameter["set"]["key"];
		value = parameter["set"]["value"];
		if(key != NULL && value != NULL) {
			g_system_settings[key] = value;
			g_util_webserial.send("syslog", "system/settings#set => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#set => ERROR");
		}
	}
	if(parameter.hasOwnProperty("get")) {
		const char* key;

		key = parameter["set"]["key"];
		if(key != NULL) {
			JSONVar data;

			if(g_system_settings.count(key) == 1) {
				data["key"] = key;
				data["value"] = g_system_settings[key].c_str();
			}
			g_util_webserial.send("system/settings#get", data);
			g_util_webserial.send("syslog", "system/settings#get => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#get => ERROR");
		}
	}
	if(parameter.hasOwnProperty("load")) {
		if(g_system_settings.load(parameter["load"]) == true) {
			g_util_webserial.send("syslog", "system/settings#load => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#load => ERROR");
		}
	}
	if(parameter.hasOwnProperty("save")) {
		if(g_system_settings.save(parameter["save"]) == true) {
			g_util_webserial.send("syslog", "system/settings#save => OK");
		} else {
			g_util_webserial.send("syslog", "system/settings#save => ERROR");
		}
	}
}


void on_system_time(JSONVar parameter) {
	if(parameter.hasOwnProperty("sync")) {
		if(parameter["sync"].hasOwnProperty("epoch")) {
			system_rp2040_set_epoch(parameter["sync"]["epoch"]);
		}
	}
	if(parameter.hasOwnProperty("config")) {
		int interval = 3600;

		if(g_system_status.count("system/time:sync/interval") == 1) {
			interval = std::stoi(g_system_status["system/time:sync/interval"]);
		}
		if(parameter["config"].hasOwnProperty("interval")) {
			interval = parameter["config"]["interval"];
		}
		setSyncProvider(system_rp2040_timelib_sync);
		setSyncInterval(interval);
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

