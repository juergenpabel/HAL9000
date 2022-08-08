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
			g_settings[key] = value;
			g_webserial.send("syslog", "system/settings#set => OK");
		} else {
			g_webserial.send("syslog", "system/settings#set => ERROR");
		}
	}
	if(parameter.hasOwnProperty("get")) {
		const char* key;

		key = parameter["set"]["key"];
		if(key != NULL) {
			JSONVar data;

			if(g_settings.count(key) == 1) {
				data["key"] = key;
				data["value"] = g_settings[key];
			}
			g_webserial.send("system/settings#get", data);
			g_webserial.send("syslog", "system/settings#get => OK");
		} else {
			g_webserial.send("syslog", "system/settings#get => ERROR");
		}
	}
	if(parameter.hasOwnProperty("load")) {
		if(g_settings.load(parameter["load"]) == true) {
			g_webserial.send("syslog", "system/settings#load => OK");
		} else {
			g_webserial.send("syslog", "system/settings#load => ERROR");
		}
	}
	if(parameter.hasOwnProperty("save")) {
		if(g_settings.save(parameter["save"]) == true) {
			g_webserial.send("syslog", "system/settings#save => OK");
		} else {
			g_webserial.send("syslog", "system/settings#save => ERROR");
		}
	}
}


void on_system_time(JSONVar parameter) {
	if(parameter.hasOwnProperty("sync")) {
		if(parameter.hasOwnProperty("epoch-seconds")) {
			rp2040_time_sync(parameter["epoch-seconds"]);
		}
	}
	if(parameter.hasOwnProperty("config")) {
		int interval = 3600;

		if(g_settings.count("system/time#interval") == 1) {
			interval = g_settings["system/time#interval"].toInt();
		}
		if(parameter["config"].hasOwnProperty("interval")) {
			interval = parameter["config"]["interval"];
		}
		setSyncProvider(rp2040_timelib_sync);
		setSyncInterval(interval);
	}
}


void on_system_reset(JSONVar parameter) {
	bool  uf2 = false;

	if(parameter.hasOwnProperty("uf2")) {
		uf2 = parameter["uf2"];
	}
	if(uf2) {
		g_webserial.send("syslog", "Resetting RP2040 with boot target UF2...");
		rp2040_reset_uf2();
	}
	g_webserial.send("syslog", "Resetting RP2040...");
	rp2040_reset();
}

