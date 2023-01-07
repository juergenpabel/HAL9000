#include <TimeLib.h>
#include <FS.h>
#include <LittleFS.h>

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
		this->m_environment.insert({key, value});
	} else {
		item->second = value;
	}
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
		this->m_settings.insert({key, value});
	} else {
		item->second = value;
	}
}


void Application::onConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<UTIL_JSON_FILESIZE_MAX> configuration;

	if(command.size() > 0) {
		JsonObject current;

		current = configuration.createNestedObject();
		current["command"].set((char*)command.c_str());
		current["data"].set(data);
	} else {
		File file;

		file = LittleFS.open("/system/application/configuration.json", "w");
		if(file == true) {
			serializeJson(configuration, file);
			file.close();
		}
		configuration.clear();
		g_application.setEnv("application/configuration", "false");
	}
}

