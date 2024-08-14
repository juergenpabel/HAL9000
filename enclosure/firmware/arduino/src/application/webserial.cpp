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
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;

	response.clear();
	if(data.containsKey("RUN") == true) {
		if(g_application.getStatus() == StatusReady) {
			g_application.setStatus(StatusRunning);
		}
		return;
	}
	if(data.containsKey("status") == true) {
		etl::string<2>  questionmark("?");

		response["status"] = JsonObject();
		if(questionmark.compare(data["status"].as<const char*>()) == 0) {
			response["status"]["name"] = g_application.getStatusName().c_str();
		} else {
			response["status"]["error"] = "unexpected value for 'status' command";
		}
	}
	if(data.containsKey("error") == true) {
		if(data["error"].containsKey("get") == true) {
			response["error"] = JsonObject();
			if(g_application.m_errors.empty() == false) {
				const Error& error = g_application.m_errors.front();

				g_application.notifyError(error.level, error.id, error.message, error.detail);
				g_application.m_errors.pop();
			}
			response["error"]["count"] = g_application.m_errors.size();
		}
	}
	if(data.containsKey("time") == true) {
		response["time"] = JsonObject();
		if(data["time"].containsKey("epoch") == true) {
			long timestamp = 0;

			timestamp = data["time"]["epoch"].as<long>();
			if(timestamp <= 1009843199 /*2001-12-31 23:59:59*/) {
				g_util_webserial.send("syslog/error", "application/runtime:time/epoch => invalid epoch timestamp");
				response["time"]["epoch"] = "error";
			} else {
				setTime(timestamp);
				response["time"]["epoch"] = "OK";
			}
		}
		if(data["time"].containsKey("synced") == true) {
			g_application.setEnv("application/runtime:time/synced", data["time"]["synced"].as<const char*>());
			response["time"]["synced"] = "OK";
		}
	}
	if(data.containsKey("shutdown") == true) {
		response["shutdown"] = JsonObject();
		if(data["shutdown"].containsKey("target") == true) {
			etl::string<10> poweroff("poweroff");
			etl::string<10> reboot("reboot");

			if(poweroff.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_application.setStatus(StatusHalting);
				response["shutdown"]["poweroff"] = "OK";
			}
			if(reboot.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_application.setStatus(StatusRebooting);
				response["shutdown"]["reboot"] = "OK";
			}
		}
	}
	g_util_webserial.send("application/runtime", response);
}


void on_application_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;

	response.clear();
	if(data.containsKey("list") == true) {
		response["list"] = JsonObject();
		for(EnvironmentMap::iterator iter=g_application.m_environment.begin(); iter!=g_application.m_environment.end(); ++iter) {
			response["list"][iter->first.c_str()] = iter->second.c_str();
		}
	}
	if(data.containsKey("get") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;

		response["get"] = JsonObject();
		key = data["get"]["key"].as<const char*>();
		if(key.length() > 0) {
			response["get"]["key"] = key.c_str();
			response["get"]["value"] = g_application.getEnv(key).c_str();
		} else {
			response["get"]["error"] = "missing 'key' parameter";
		}
	}
	if(data.containsKey("set") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		response["set"] = JsonObject();
		key = data["set"]["key"].as<const char*>();
		value = data["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_application.setEnv(key, value);
			response["set"]["key"] = key.c_str();
			response["set"]["value"] = value.c_str();
		} else {
			response["set"]["error"] = "missing 'key' and/or 'value' parameter";
		}
	}
	g_util_webserial.send("application/environment", response);
}


void on_application_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;

	response.clear();
	if(data.containsKey("list") == true) {
		response["list"] = JsonObject();
		for(SettingsMap::iterator iter=g_application.m_settings.begin(); iter!=g_application.m_settings.end(); ++iter) {
			response["list"][iter->first.c_str()].set((char*)iter->second.c_str());
		}
	}
	if(data.containsKey("get") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;

		response["get"] = JsonObject();
		key = data["get"]["key"].as<const char*>();
		if(key.length() > 0) {
			response["get"]["key"] = key.c_str();
			if(g_application.hasSetting(key) == true) {
				response["get"]["value"] = g_application.getSetting(key).c_str();
			} else {
				response["get"]["value"] = (char*)0;
			}
		} else {
			response["get"]["error"] = "missing 'key' parameter";
		}
	}
	if(data.containsKey("set") == true) {
		etl::string<GLOBAL_KEY_SIZE> key;
		etl::string<GLOBAL_VALUE_SIZE> value;

		response["set"] = JsonObject();
		key = data["set"]["key"].as<const char*>();
		value = data["set"]["value"].as<const char*>();
		if(key.length() > 0 && value.length() > 0) {
			g_application.setSetting(key, value);
			response["set"]["key"] = key.c_str();
			response["set"]["value"] = value.c_str();
		} else {
			response["set"]["error"] = "missing 'key' and/or 'value' parameter";
		}
	}
	if(data.containsKey("load") == true) {
		response["load"] = JsonObject();
		if(g_application.loadSettings() == true) {
			response["load"]["size"] = g_application.m_settings.size();
		} else {
			response["load"]["error"] = "Application::loadSettings() returned false";
		}
	}
	if(data.containsKey("save") == true) {
		response["save"] = JsonObject();
		if(g_application.saveSettings() == true) {
			response["save"]["size"] = g_application.m_settings.size();
		} else {
			response["save"]["error"] = "Application::saveSettings() returned false";
		}
	}
	if(data.containsKey("reset") == true) {
		response["reset"] = JsonObject();
		if(g_application.resetSettings() == true) {
			response["reset"]["size"] = g_application.m_settings.size();
		} else {
			response["reset"]["error"] = "Application::resetSettings() returned false";
		}
	}
	g_util_webserial.send("application/settings", response);
}

