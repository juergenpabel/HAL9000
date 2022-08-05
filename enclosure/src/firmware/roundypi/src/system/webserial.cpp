#include <TimeLib.h>
#include <JSONVar.h>
#include "system/webserial.h"
#include "system/rp2040.h"
#include "globals.h"


void on_system_settings(JSONVar parameter) {
	if(parameter.hasOwnProperty("load")) {
		if(g_settings.load(parameter["load"]) == true) {
			g_webserial.send("RoundyPI", "system:settings#load => OK");
		} else {
			g_webserial.send("RoundyPI", "system:settings#load => ERROR");
		}
	}
	if(parameter.hasOwnProperty("save")) {
		if(g_settings.save(parameter["save"]) == true) {
			g_webserial.send("RoundyPI", "system:settings#save => OK");
		} else {
			g_webserial.send("RoundyPI", "system:settings#save => ERROR");
		}
	}
}


void on_system_time(JSONVar parameter) {
	if(parameter.hasOwnProperty("epoch-seconds")) {
		rp2040_time_set(parameter["epoch-seconds"]);
	} else {
		int interval = 3600;

		if(g_settings.count("system:time#interval") == 1) {
			interval = g_settings["system:time#interval"].toInt();
		}
		if(parameter.hasOwnProperty("interval")) {
			interval = parameter["interval"];
		}
		setSyncProvider(rp2040_time_sync);
		setSyncInterval(interval);
	}
}


void on_system_reset(JSONVar parameter) {
	bool  uf2 = false;

	if(parameter.hasOwnProperty("uf2")) {
		uf2 = parameter["uf2"];
	}
	if(uf2) {
		g_webserial.send("RoundyPI", "Resetting RP2040 with boot target UF2...");
		rp2040_reset_uf2();
	}
	g_webserial.send("RoundyPI", "Resetting RP2040...");
	rp2040_reset();
}

