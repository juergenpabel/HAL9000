#include <TimeLib.h>
#include <FS.h>
#include <LittleFS.h>
#include <etl/string.h>

#include "application/application.h"
#include "globals.h"


const etl::string<GLOBAL_VALUE_SIZE> Application::Null;


Application::Application() 
            :m_status(StatusUnknown)
            ,m_condition(ConditionAwake)
            ,m_environment()
            ,m_settings("/system/application/settings.ini") {
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


static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> g_application_configuration;


void Application::onConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	if(command.size() > 0) {
		JsonObject current;

		current = g_application_configuration.createNestedObject();
		current["command"].set((char*)command.c_str());
		current["data"].set(data);
	} else {
		File file;

		file = LittleFS.open("/system/application/configuration.json", "w");
		if(file == true) {
			serializeJson(g_application_configuration, file);
			file.close();
		}
		g_application_configuration.clear();
		g_application.setEnv("application/configuration", "false");
	}
}


void Application::onRunning() {
	while(this->m_errors.empty() == false) {
		const Error& error = this->m_errors.front();

		this->notifyError(error.level, error.code, error.message, error.timeout);
		this->m_errors.pop();
	}
	g_application_configuration.clear();
	if(LittleFS.exists("/system/application/configuration.json") == true) {
		File file;

		file = LittleFS.open("/system/application/configuration.json", "r");
		if(file == true) {
			if(deserializeJson(g_application_configuration, file) != DeserializationError::Ok) {
				g_application.notifyError("error", "004", "JSON error in application config");
				g_application_configuration.clear();
			}
			if(g_application_configuration.isNull() == false) {
				for(JsonObject item : g_application_configuration.as<JsonArray>()) {
					if(item.containsKey("command") == true && item.containsKey("data") == true) {
						g_util_webserial.handle(item["command"].as<const char*>(), item["data"].as<JsonVariant>());
					}
				}
			}
			file.close();
		}
	}
}


void Application::notifyError(const etl::string<GLOBAL_KEY_SIZE>& level, const etl::string<GLOBAL_KEY_SIZE>& code, const etl::string<GLOBAL_VALUE_SIZE>& message, uint16_t timeout) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> webserial_body;

	if(this->getStatus() != StatusRunning) {
		if(this->m_errors.full() == true) {
			this->m_errors.pop();
		}
		this->m_errors.push(Error(level, code, message, timeout));
		return;
	}
	webserial_body.clear();
	webserial_body.createNestedObject("error");
	webserial_body["error"]["level"] = level.c_str();
	webserial_body["error"]["code"] = code.c_str();
	webserial_body["error"]["message"] = message.c_str();
	webserial_body["error"]["timeout"] = timeout;
	g_util_webserial.send("application/event", webserial_body);
}

