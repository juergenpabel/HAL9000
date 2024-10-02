#include <TimeLib.h>
#include <ArduinoJson.h>
#include <etl/string.h>
#include <etl/to_string.h>
#include <etl/format_spec.h>

#include "device/microcontroller/include.h"
#include "system/application.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/animations/screen.h"
#include "globals.h"


void on_system_runlevel(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& payload) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;
	       Runlevel                                  runlevel;

	response.clear();
	runlevel = g_system_application.getRunlevel();
	if(etl::string<GLOBAL_KEY_SIZE>("").compare(payload.as<const char*>()) == 0) {
		g_util_webserial.send("system/runlevel", g_system_application.getRunlevelName());
		if(runlevel == RunlevelPanicing) {
			g_util_webserial.send("syslog/info", "Arduino has panic'ed, dumping environment and settings next:");
			for(EnvironmentMap::iterator iter=g_system_application.environment.begin(); iter!=g_system_application.environment.end(); ++iter) {
				response.clear();
				response["environment"] = JsonObject();
				response["environment"][iter->first] = iter->second;
				g_util_webserial.send("syslog/info", response);
			}
			for(SettingsMap::iterator iter=g_system_application.settings.begin(); iter!=g_system_application.settings.end(); ++iter) {
				response.clear();
				response["setting"] = JsonObject();
				response["setting"][iter->first] = iter->second;
				g_util_webserial.send("syslog/info", response);
			}
		}
		return;
	}
	if(runlevel != RunlevelPanicing) {
		if(etl::string<GLOBAL_KEY_SIZE>("panicing").compare(payload.as<const char*>()) == 0) {
			g_system_application.setRunlevel(RunlevelPanicing);
			g_util_webserial.send("system/runlevel", g_system_application.getRunlevelName());
			return;
		}
		if(etl::string<GLOBAL_KEY_SIZE>("kill").compare(payload.as<const char*>()) == 0) {
			if(gui_screen_getname().compare("animations:system-terminating") == 0) {
				g_system_application.setEnv("gui/screen:animations/loop", "false");
				while(gui_screen_get() != gui_screen_none) {
					gui_update();
					delay(10);
				}
			}
			switch(runlevel) {
				case RunlevelHalting:
					g_device_board.displayOff();
					g_device_board.halt();
					break;
				case RunlevelRestarting:
					g_device_board.displayOn();
					g_device_board.reset();
					break;
				default:
					g_system_application.processError("panic", "219", "Application killed", "Application execution terminated due to webserial request " \
					                                                                 "'system/runlevel' with (unexpected) operation 'kill'");
			}
			return;
		}
	}
	switch(runlevel) {
		case RunlevelStarting:
			if(etl::string<GLOBAL_KEY_SIZE>("configuring").compare(payload.as<const char*>()) == 0) {
				g_system_application.setRunlevel(RunlevelConfiguring);
			}
			break;
		case RunlevelConfiguring:
			if(etl::string<GLOBAL_KEY_SIZE>("ready").compare(payload.as<const char*>()) == 0) {
				g_system_application.setRunlevel(RunlevelReady);
			}
			break;
		case RunlevelReady:
			if(etl::string<GLOBAL_KEY_SIZE>("running").compare(payload.as<const char*>()) == 0) {
				g_system_application.setRunlevel(RunlevelRunning);
			}
			//no break as 'ready' => ['restarting'|'halting'] is also permitted
		case RunlevelRunning:
			if(etl::string<GLOBAL_KEY_SIZE>("restarting").compare(payload.as<const char*>()) == 0) {
				g_system_application.setRunlevel(RunlevelRestarting);
			}
			if(etl::string<GLOBAL_KEY_SIZE>("halting").compare(payload.as<const char*>()) == 0) {
				g_system_application.setRunlevel(RunlevelHalting);
			}
			break;
		default:
			g_util_webserial.send("syslog/info", "Arduino is already in a final runlevel (restarting, halting or panicinc), " \
			                                     "ignoring runlevel change request");
	}
	g_util_webserial.send("system/runlevel", g_system_application.getRunlevelName());
}


void on_system_features(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;

	response.clear();
	if(data.containsKey("time") == true) {
		response["time"] = JsonObject();
		if(data["time"].containsKey("epoch") == true) {
			long timestamp = 0;

			timestamp = data["time"]["epoch"].as<long>();
			if(timestamp > 1009843199 /*2001-12-31 23:59:59*/) {
				response["result"] = "OK";
				g_system_application.setTime(timestamp);
			} else {
				response["result"] = "error";
				response["error"]["id"] = "216";
				response["error"]["level"] = "warn";
				response["error"]["title"] = "Invalid request";
				response["error"]["details"] = "request for topic 'system/runlevel' with operation 'time' has invalid value for parameter 'epoch')";
				response["error"]["data"] = JsonObject();
				response["error"]["data"]["epoch"] = timestamp;
			}
		}
		if(response.containsKey("error") == false) {
			if(data["time"].containsKey("synced") == true) {
				g_system_application.setEnv("system/features:time/synced", data["time"]["synced"].as<const char*>());
				response["result"] = "OK";
			}
		}
	}
	g_util_webserial.send("system/features", response);
}

void on_system_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;
	static etl::string<GLOBAL_KEY_SIZE>              key;
	static etl::string<GLOBAL_VALUE_SIZE>            value;

	response.clear();
	key.clear();
	value.clear();
	if(data.containsKey("list") == true) {
		response["list"] = JsonObject();
		for(EnvironmentMap::iterator iter=g_system_application.environment.begin(); iter!=g_system_application.environment.end(); ++iter) {
			response["list"][iter->first] = iter->second;
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
			response["get"]["key"] = key;
			response["get"]["value"] = g_system_application.getEnv(key);
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'system/environment' with operation 'get' has missing/empty value for parameter 'key')";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key;
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
		if(key.length() > 0) {
			g_system_application.setEnv(key, value);
			response["result"] = "OK";
			response["set"]["key"] = key;
			response["set"]["value"] = value;
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'system/environment' with operation 'set' has missing/empty value for parameter 'key')";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key;
			response["error"]["data"]["value"] = value;
		}
	}
	g_util_webserial.send("system/environment", response);
}


void on_system_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> response;
	static etl::string<GLOBAL_KEY_SIZE>              key;
	static etl::string<GLOBAL_VALUE_SIZE>            value;

	response.clear();
	key.clear();
	value.clear();
	if(data.containsKey("list") == true) {
		response["list"] = JsonObject();
		for(SettingsMap::iterator iter=g_system_application.settings.begin(); iter!=g_system_application.settings.end(); ++iter) {
			response["list"][iter->first] = iter->second;
		}
		response["result"] = "OK";
	}
	if(data.containsKey("get") == true) {
		response["get"] = JsonObject();
		if(data["get"].containsKey("key") == true) {
			key = data["get"]["key"].as<const char*>();
		}
		if(key.length() > 0) {
			response["get"]["key"] = key;
			if(g_system_application.hasSetting(key) == true) {
				response["get"]["value"] = g_system_application.getSetting(key);
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
			response["error"]["details"] = "request for topic 'system/settings' with operation 'get' has missing/empty value for parameter 'key'";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key;
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
			g_system_application.setSetting(key, value);
			response["result"] = "OK";
			response["set"]["key"] = key;
			response["set"]["value"] = value;
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "216";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Invalid request";
			response["error"]["details"] = "request for topic 'system/settings' with operation 'set' has missing/empty value for parameters " \
			                               "'key' and/or 'value')";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["key"] = key;
			response["error"]["data"]["value"] = value;
		}
	}
	if(data.containsKey("load") == true) {
		response["load"] = JsonObject();
		if(g_system_application.loadSettings() == true) {
			response["result"] = "OK";
			response["load"]["size"] = g_system_application.settings.size();
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "215";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Application error";
			response["error"]["details"] = "request for topic 'system/settings' with operation 'load': Application::loadSettings() failed";
			response["error"]["data"] = JsonObject();
		}
	}
	if(data.containsKey("save") == true) {
		response["save"] = JsonObject();
		if(g_system_application.saveSettings() == true) {
			response["result"] = "OK";
			response["save"]["size"] = g_system_application.settings.size();
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "215";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Application error";
			response["error"]["details"] = "request for topic 'system/settings' with operation 'save': Application::saveSettings() failed";
			response["error"]["data"] = JsonObject();
		}
	}
	if(data.containsKey("reset") == true) {
		response["reset"] = JsonObject();
		if(g_system_application.resetSettings() == true) {
			response["result"] = "OK";
			response["reset"]["size"] = g_system_application.settings.size();
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "215";
			response["error"]["level"] = "warn";
			response["error"]["title"] = "Application error";
			response["error"]["details"] = "request for topic 'system/settings' with operation 'reset': Application::resetSettings() failed";
			response["error"]["data"] = JsonObject();
		}
	}
	g_util_webserial.send("system/settings", response);
}

