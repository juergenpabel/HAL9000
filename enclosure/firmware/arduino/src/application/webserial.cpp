#include <TimeLib.h>
#include <ArduinoJson.h>
#include <etl/string.h>
#include <etl/to_string.h>
#include <etl/format_spec.h>

#include "device/microcontroller/include.h"
#include "application/application.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/animations/screen.h"
#include "globals.h"


void on_application_runtime(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;

	response.clear();
	if(data.containsKey("INTERNAL:CONFIG") == true) {
		if(g_application.getStatus() == StatusStarting) {
			g_application.setStatus(StatusConfiguring);
			gui_screen_set("system-configuring", gui_screen_animations_system_configuring);
			return;
		}
		response["result"] = "error";
		response["error"] = JsonObject();
		response["error"]["id"] = "216";
		response["error"]["level"] = "warn";
		response["error"]["title"] = "Invalid request";
		response["error"]["details"] = "request for topic 'application/runtime' with operation 'INTERNAL:CONFIG' "
		                               "only valid in status 'starting'";
	}
	if(data.containsKey("INTERNAL:QUIT") == true) {
		switch(g_application.getStatus()) {
			case StatusHalting:
				g_device_board.halt();
				break;
			case StatusRebooting:
				g_device_board.reset();
				break;
			default:
				response["result"] = "error";
				response["error"] = JsonObject();
				response["error"]["id"] = "216";
				response["error"]["level"] = "warn";
				response["error"]["title"] = "Invalid request";
				response["error"]["details"] = "request for topic 'application/runtime' with operation 'INTERNAL:QUIT' "
				                               "only valid in status 'halting' or 'rebooting'";
		}
	}
	if(data.containsKey("status") == true) {
		static etl::string<2>  questionmark("?");

		response["status"] = JsonObject();
		if(questionmark.compare(data["status"].as<const char*>()) == 0) {
			response["result"] = "OK";
			response["status"]["name"] = g_application.getStatusName().c_str();
			if(g_application.getStatus() == StatusPanicing) {
				if(g_application.hasEnv("application/status:panicing/error") == true) {
					response["status"]["error"] = g_application.getEnv("application/status:panicing/error");
				}
			}
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'application/runtime' with operation 'status' has invalid parameter (only '?' is valid)";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["status"] = data["status"].as<const char*>();
		}
	}
	if(data.containsKey("time") == true) {
		response["time"] = JsonObject();
		if(data["time"].containsKey("epoch") == true) {
			long timestamp = 0;

			timestamp = data["time"]["epoch"].as<long>();
			if(timestamp > 1009843199 /*2001-12-31 23:59:59*/) {
				response["result"] = "OK";
				g_application.setTime(timestamp);
			} else {
				g_util_webserial.send("syslog/error", "application/runtime:time/epoch => invalid epoch timestamp");
				response["result"] = "error";
				response["error"]["id"] = "216";
				response["error"]["level"] = "warn";
				response["error"]["title"] = "Invalid request";
				response["error"]["details"] = "request for topic 'application/runtime' with operation 'time' has invalid value for parameter 'epoch')";
				response["error"]["data"] = JsonObject();
				response["error"]["data"]["epoch"] = timestamp;
			}
		}
		if(response.containsKey("error") == false) {
			if(data["time"].containsKey("synced") == true) {
				g_application.setEnv("application/runtime:time/synced", data["time"]["synced"].as<const char*>());
				response["result"] = "OK";
			}
		}
	}
	if(data.containsKey("shutdown") == true) {
		response["shutdown"] = JsonObject();
		if(data["shutdown"].containsKey("target") == true) {
			etl::string<10> poweroff("poweroff");
			etl::string<10> reboot("reboot");

			if(poweroff.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_application.setStatus(StatusHalting);
				response["result"] = "OK";
			}
			if(reboot.compare(data["shutdown"]["target"].as<const char*>()) == 0) {
				g_application.setStatus(StatusRebooting);
				response["result"] = "OK";
			}
		}
		if(response.containsKey("result") == false) {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'application/runtime' with operation 'shutdown' has invalid value for parameter 'target')";
			response["error"]["data"] = JsonObject();
			if(data["shutdown"].containsKey("target") == true) {
				response["error"]["data"]["target"] = data["shutdown"]["target"].as<const char*>();
			} else {
				response["error"]["data"]["target"] = (const char*)nullptr;
			}
		}
	}
	g_util_webserial.send("application/runtime", response);
}


void on_application_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;
	static etl::string<GLOBAL_KEY_SIZE>              key;
	static etl::string<GLOBAL_VALUE_SIZE>            value;

	response.clear();
	key.clear();
	value.clear();
	if(data.containsKey("list") == true) {
		response["list"] = JsonObject();
		for(EnvironmentMap::iterator iter=g_application.m_environment.begin(); iter!=g_application.m_environment.end(); ++iter) {
			response["list"][iter->first.c_str()] = iter->second.c_str();
		}
		response["result"] = "OK";
	}
	if(data.containsKey("get") == true) {
		response["get"] = JsonObject();
		if(data["get"].containsKey("key") == true) {
			key = data["get"]["key"].as<const char*>();
		}
		if(key.length() > 0) {
			response["result"] = "OK";
			response["get"]["key"] = key.c_str();
			response["get"]["value"] = g_application.getEnv(key).c_str();
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'application/environment' with operation 'get' has missing/empty value for parameter 'key')";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key.c_str();
		}
	}
	if(data.containsKey("set") == true) {
		response["set"] = JsonObject();
		if(data["set"].containsKey("key") == true) {
			key = data["set"]["key"].as<const char*>();
		}
		if(data["set"].containsKey("value") == true) {
			value = data["set"]["value"].as<const char*>();
		}
		if(key.length() > 0 && value.length() > 0) {
			g_application.setEnv(key, value);
			response["set"]["key"] = key.c_str();
			response["set"]["value"] = value.c_str();
			response["result"] = "OK";
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'application/environment' with operation 'set' has missing/empty value for parameters " \
			                               "'key' and/or 'value')";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key.c_str();
			response["error"]["data"]["value"] = value.c_str();
		}
	}
	g_util_webserial.send("application/environment", response);
}


void on_application_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;
	static etl::string<GLOBAL_KEY_SIZE>              key;
	static etl::string<GLOBAL_VALUE_SIZE>            value;

	response.clear();
	key.clear();
	value.clear();
	if(data.containsKey("list") == true) {
		response["list"] = JsonObject();
		for(SettingsMap::iterator iter=g_application.m_settings.begin(); iter!=g_application.m_settings.end(); ++iter) {
			response["list"][iter->first.c_str()].set((char*)iter->second.c_str());
		}
		response["result"] = "OK";
	}
	if(data.containsKey("get") == true) {
		response["get"] = JsonObject();
		if(data["get"].containsKey("key") == true) {
			key = data["get"]["key"].as<const char*>();
		}
		if(key.length() > 0) {
			response["get"]["key"] = key.c_str();
			if(g_application.hasSetting(key) == true) {
				response["get"]["value"] = g_application.getSetting(key).c_str();
			} else {
				response["get"]["value"] = (const char*)nullptr;
			}
			response["result"] = "OK";
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'application/settings' with operation 'get' has missing/empty value for parameter 'key'";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key.c_str();
		}
	}
	if(data.containsKey("set") == true) {
		response["set"] = JsonObject();
		if(data["set"].containsKey("key") == true) {
			key = data["set"]["key"].as<const char*>();
		}
		if(data["set"].containsKey("value") == true) {
			value = data["set"]["value"].as<const char*>();
		}
		if(key.length() > 0 && value.length() > 0) {
			g_application.setSetting(key, value);
			response["result"] = "OK";
			response["set"]["key"] = key.c_str();
			response["set"]["value"] = value.c_str();
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'application/settings' with operation 'set' has missing/empty value for parameters " \
			                               "'key' and/or 'value')";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key.c_str();
			response["error"]["data"]["value"] = value.c_str();
		}
	}
	if(data.containsKey("load") == true) {
		response["load"] = JsonObject();
		if(g_application.loadSettings() == true) {
			response["result"] = "OK";
			response["load"]["size"] = g_application.m_settings.size();
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "215";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Application error";
			response["error"]["details"] = "request for topic 'application/settings' with operation 'load': Application::loadSettings() failed";
			response["error"]["data"] = JsonObject();
		}
	}
	if(data.containsKey("save") == true) {
		response["save"] = JsonObject();
		if(g_application.saveSettings() == true) {
			response["save"]["size"] = g_application.m_settings.size();
			response["result"] = "OK";
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "215";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Application error";
			response["error"]["details"] = "request for topic 'application/settings' with operation 'save': Application::saveSettings() failed";
			response["error"]["data"] = JsonObject();
		}
	}
	if(data.containsKey("reset") == true) {
		response["reset"] = JsonObject();
		if(g_application.resetSettings() == true) {
			response["reset"]["size"] = g_application.m_settings.size();
			response["result"] = "OK";
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "215";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Application error";
			response["error"]["details"] = "request for topic 'application/settings' with operation 'reset': Application::resetSettings() failed";
			response["error"]["data"] = JsonObject();
		}
	}
	g_util_webserial.send("application/settings", response);
}

