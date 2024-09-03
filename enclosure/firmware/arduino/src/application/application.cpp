#include <TimeLib.h>
#include <FS.h>
#include <LittleFS.h>
#include <etl/string.h>

#include "application/application.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/animations/screen.h"
#include "globals.h"


       const etl::string<GLOBAL_VALUE_SIZE> Application::Null;
static const etl::string<GLOBAL_KEY_SIZE> ApplicationStatusNames[] = { "unknown", "starting", "configuring", "ready",
                                                                       "running", "rebooting", "halting", "panicing" };


Application::Application() 
            :m_status(StatusUnknown)
            ,m_time_offset(0)
            ,m_errors()
            ,m_environment()
            ,m_settings("/system/application/settings.ini") {
}


const etl::string<GLOBAL_KEY_SIZE>& Application::getStatusName() {
	return ApplicationStatusNames[this->m_status];
}


void Application::setTime(time_t time) {
	this->m_time_offset = time - (millis()/1000);
}


time_t Application::getTime() {
	return g_application.m_time_offset + (millis()/1000);
}


bool Application::loadSettings() {
	this->m_settings.reset();
	return this->m_settings.load();
}


bool Application::saveSettings() {
	return this->m_settings.save();
}


bool Application::resetSettings() {
	return this->m_settings.reset();
}


bool Application::hasEnv(const etl::string<GLOBAL_KEY_SIZE>& key) {
	return this->m_environment.find(key) != this->m_environment.end();
}


const etl::string<GLOBAL_VALUE_SIZE>& Application::getEnv(const etl::string<GLOBAL_KEY_SIZE>& key) {
	EnvironmentMap::iterator item;

	item = this->m_environment.find(key);
	if(item == this->m_environment.end()) {
		return Application::Null;
	}
	return item->second;
}


void Application::setEnv(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value) {
	EnvironmentMap::iterator item;

	item = this->m_environment.find(key);
	if(item == this->m_environment.end()) {
		if(value != Application::Null) {
			this->m_environment.insert({key, value});
		}
	} else {
		if(value != Application::Null) {
			item->second = value;
		} else {
			this->m_environment.erase(item);
		}
	}
}


void Application::delEnv(const etl::string<GLOBAL_KEY_SIZE>& key) {
	this->m_environment.erase(key);
}


bool Application::hasSetting(const etl::string<GLOBAL_KEY_SIZE>& key) {
	return this->m_settings.find(key) != this->m_settings.end();
}


const etl::string<GLOBAL_VALUE_SIZE>& Application::getSetting(const etl::string<GLOBAL_KEY_SIZE>& key) {
	SettingsMap::iterator item;

	item = this->m_settings.find(key);
	if(item == this->m_settings.end()) {
		return Application::Null;
	}
	return item->second;
}


void Application::setSetting(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value) {
	SettingsMap::iterator item;

	item = this->m_settings.find(key);
	if(item == this->m_settings.end()) {
		if(value != Application::Null) {
			this->m_settings.insert({key, value});
		}
	} else {
		if(value != Application::Null) {
			item->second = value;
		} else {
			this->m_settings.erase(item);
		}
	}
}


void Application::delSetting(const etl::string<GLOBAL_KEY_SIZE>& key) {
	this->m_settings.erase(key);
}


void Application::onConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> configuration;
	       JsonObject                                          current;

	switch(g_application.getStatus()) {
		case StatusConfiguring:
			if(command != "") { // non-empty line means configuration instruction
				if(g_util_webserial.hasCommand(command) == true) {
					current = configuration.createNestedObject();
					current["command"].set((char*)command.c_str());
					current["data"].set(data);
				}
			}
			if(command == "") { // empty line means end-of-configuration
				if(configuration.size() > 0) {
					File file;

					g_util_webserial.send("syslog/debug", "saving application configuration to (littlefs:)" \
					                                      "'/system/application/configuration.json'");
					file = LittleFS.open("/system/application/configuration.json", "w");
					if(file == true) {
						serializeJson(configuration, file);
						file.close();
						configuration.clear();
						g_util_webserial.send("syslog/debug", "saved application configuration to (littlefs:)" \
						                                      "'/system/application/configuration.json'");
					} else {
						g_util_webserial.send("syslog/warn", "failed to open (littlefs:)'/system/application/configuration.json' in " \
						                                     "write-mode, unable to persist configuration for future application startups");
					}
				}
				g_application.setStatus(StatusReady);
			}
			break;
		case StatusRunning:
			if(configuration.size() == 0) {
				if(LittleFS.exists("/system/application/configuration.json") == true) {
					File file;

					file = LittleFS.open("/system/application/configuration.json", "r");
					if(file == true) {
						configuration.clear();
						if(deserializeJson(configuration, file) == DeserializationError::Ok) {
							g_util_webserial.send("syslog/debug", "application configuration loaded from (littlefs:)" \
							                                      "'/system/application/configuration.json'");
						} else {
							g_application.notifyError("error", "12", "Configuration error", "JSON error in (littlefs:)" \
							                                                                "'/system/application/configuration.json'");
							configuration.clear();
						}
						file.close();
					} else {
						g_application.notifyError("error", "14", "Config file error", "failed to open *supposedly existing* (littlefs:)" \
						                                                              "'/system/application/configuration.json' in " \
						                                                              "read-mode (probably need to reflash littlefs)");
					}
				} else {
					g_application.notifyError("error", "15", "No config file", "file not found in (littlefs:)" \
					                                                           "'/system/application/configuration.json'");
				}
			}
			if(configuration.size() > 0) {
				g_util_webserial.send("syslog/debug", "activating application configuration...");
				for(JsonObject item : configuration.as<JsonArray>()) {
					if(item.containsKey("command") == true && item.containsKey("data") == true) {
						g_util_webserial.handle(item["command"].as<const char*>(), item["data"].as<JsonVariant>());
					}
				}
				configuration.clear();
				g_util_webserial.send("syslog/debug", "...application configuration activated");
			}
			break;
		default:
			etl::string<GLOBAL_VALUE_SIZE> log_message("Application::onConfiguration() called in unexpected application-status: ");

			log_message += g_application.getStatusName();
			g_util_webserial.send("syslog/warn", log_message);
	}
}


void Application::notifyError(const etl::string<GLOBAL_KEY_SIZE>& level, const etl::string<GLOBAL_KEY_SIZE>& id,
                              const etl::string<GLOBAL_VALUE_SIZE>& message, const etl::string<GLOBAL_VALUE_SIZE>& detail) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> webserial_body;

	if(this->getStatus() != StatusRunning) {
		if(this->m_errors.full() == true) {
			this->m_errors.pop();
		}
		this->m_errors.push(Error(level, id, message, detail));
		return;
	}
	webserial_body.clear();
	webserial_body.createNestedObject("error");
	webserial_body["error"]["level"] = level.c_str();
	webserial_body["error"]["id"] = id.c_str();
	webserial_body["error"]["message"] = message.c_str();
	webserial_body["error"]["detail"] = detail.c_str();
	g_util_webserial.send("application/error", webserial_body);
}

