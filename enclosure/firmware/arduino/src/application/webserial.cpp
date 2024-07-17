#include <TimeLib.h>
#include <ArduinoJson.h>
#include <etl/string.h>
#include <etl/to_string.h>
#include <etl/format_spec.h>

#include "device/microcontroller/include.h"
#include "application/application.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "globals.h"


void on_application_runtime(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

	json.clear();
	if(data.containsKey("ready") == true) {
		if(g_application.getStatus() == StatusWaiting) {
			g_application.setStatus(StatusReady);
		}
	}
	if(data.containsKey("status") == true) {
		json["status"] = g_application.getStatusName();
		g_util_webserial.send("application/runtime", json);
	}
	if(data.containsKey("time") == true) {
		if(data["time"].containsKey("epoch") == true) {
			long timestamp = 0;

			timestamp = data["time"]["epoch"].as<long>();
			if(timestamp <= 1009843199 /*2001-12-31 23:59:59*/) {
				g_util_webserial.send("syslog/error", "application/runtime:time/epoch => invalid epoch timestamp");
				return;
			}
			setTime(timestamp);
			g_util_webserial.send("syslog/debug", "application/runtime:time/epoch => OK");
		}
		if(data["time"].containsKey("synced") == true) {
			g_application.setEnv("application/runtime:time/synced", data["time"]["synced"].as<const char*>());
			g_util_webserial.send("syslog/debug", "application/runtime:time/synced => OK");
		}
	}
	if(data.containsKey("shutdown") == true) {
		if(data["shutdown"].containsKey("target") == true) {
			etl::string<10> poweroff("poweroff");
			etl::string<10> reboot("reboot");

			if(poweroff.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_application.setStatus(StatusHalting);
				g_util_webserial.send("syslog/debug", "application/runtime:shutdown/target=poweroff");
			}
			if(reboot.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_application.setStatus(StatusRebooting);
				g_util_webserial.send("syslog/debug", "application/runtime:shutdown/target=reboot");
			}
		}
	}
}


void on_application_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

	json.clear();
	if(data.containsKey("list") == true) {
		for(EnvironmentMap::iterator iter=g_application.m_environment.begin(); iter!=g_application.m_environment.end(); ++iter) {
			json[iter->first.c_str()] = iter->second.c_str();
		}
		g_util_webserial.send("application/environment:list", json.as<JsonVariant>());
		g_util_webserial.send("syslog/debug", "application/environment:list => OK");
	}
	if(data.containsKey("get") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;

		key = data["get"]["key"].as<const char*>();
		if(key.length() > 0) {
			g_util_webserial.send("application/environment:get", g_application.getEnv(key));
			g_util_webserial.send("syslog/debug", "application/environment:get => OK");
		} else {
			g_util_webserial.send("syslog/error", "application/environment:get => ERROR");
		}
	}
	if(data.containsKey("set") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = data["set"]["key"].as<const char*>();
		value = data["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_application.setEnv(key, value);
			g_util_webserial.send("syslog/debug", "application/environment:set => OK");
		} else {
			g_util_webserial.send("syslog/error", "application/environment:set => ERROR");
		}
	}
}


void on_application_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

	json.clear();
	if(data.containsKey("list") == true) {
		for(SettingsMap::iterator iter=g_application.m_settings.begin(); iter!=g_application.m_settings.end(); ++iter) {
			json[iter->first.c_str()].set((char*)iter->second.c_str());
		}
		g_util_webserial.send("application/settings:list", json);
		g_util_webserial.send("syslog/debug", "application/settings:list => OK");
	}
	if(data.containsKey("get") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;

		key = data["get"]["key"].as<const char*>();
		if(key.length() > 0) {
			if(g_application.hasSetting(key) == true) {
				json["key"] = key.c_str();
				json["value"] = g_application.getSetting(key).c_str();
			}
			g_util_webserial.send("application/settings:get", json);
			g_util_webserial.send("syslog/debug", "application/settings:get => OK");
		} else {
			g_util_webserial.send("syslog/error", "application/settings:get => ERROR");
		}
	}
	if(data.containsKey("set") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		key = data["set"]["key"].as<const char*>();
		value = data["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_application.setSetting(key, value);
			g_util_webserial.send("syslog/debug", "application/settings:set => OK");
		} else {
			g_util_webserial.send("syslog/error", "application/settings:set => ERROR");
		}
	}
	if(data.containsKey("load") == true) {
		if(g_application.loadSettings() == true) {
			g_util_webserial.send("syslog/debug", "application/settings:load => OK");
		} else {
			g_util_webserial.send("syslog/error", "application/settings:load => ERROR");
		}
	}
	if(data.containsKey("save") == true) {
		if(g_application.saveSettings() == true) {
			g_util_webserial.send("syslog/debug", "application/settings:save => OK");
		} else {
			g_util_webserial.send("syslog/error", "application/settings:save => ERROR");
		}
	}
	if(data.containsKey("reset") == true) {
		if(g_application.resetSettings() == true) {
			g_util_webserial.send("syslog/debug", "application/settings:reset => OK");
		} else {
			g_util_webserial.send("syslog/error", "application/settings:reset => ERROR");
		}
	}
}

