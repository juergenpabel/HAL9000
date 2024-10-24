#include <TimeLib.h>
#include <FS.h>
#include <LittleFS.h>
#include <etl/string.h>

#include "system/application.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/animations/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


       const etl::string<GLOBAL_VALUE_SIZE> Application::Null;
static const etl::string<GLOBAL_KEY_SIZE>   ApplicationRunlevelNames[] = { "unknown", "starting", "configuring", "ready",
                                                                           "running", "restarting", "halting", "panicing" };


Application::Application() 
            :runlevel(RunlevelStarting)
            ,time_offset(0)
            ,error_context()
            ,configuration()
            ,environment()
            ,settings("/system/settings.ini") {
}


void Application::setRunlevel(Runlevel runlevel) {
	if(runlevel > this->runlevel && runlevel <= RunlevelMAX) {
		this->runlevel = runlevel;
	}
}


Runlevel Application::getRunlevel() {
	return this->runlevel;
}


const etl::string<GLOBAL_KEY_SIZE>& Application::getRunlevelName() {
	return ApplicationRunlevelNames[this->runlevel];
}


void Application::setTime(time_t time) {
	if(this->time_offset == 0) {
		setSyncProvider(Application::getTime);
		setSyncInterval(3600);
	}
	this->time_offset = time - (millis()/1000);
	::setTime(time);
}


time_t Application::getTime() {
	return g_system_application.time_offset + (millis()/1000);
}


bool Application::loadSettings() {
	this->settings.reset();
	return this->settings.load();
}


bool Application::saveSettings() {
	return this->settings.save();
}


bool Application::resetSettings() {
	return this->settings.reset();
}


bool Application::hasEnv(const etl::string<GLOBAL_KEY_SIZE>& key) {
	return this->environment.find(key) != this->environment.end();
}


const etl::string<GLOBAL_VALUE_SIZE>& Application::getEnv(const etl::string<GLOBAL_KEY_SIZE>& key) {
	EnvironmentMap::iterator item;

	item = this->environment.find(key);
	if(item == this->environment.end()) {
		return Application::Null;
	}
	return item->second;
}


void Application::setEnv(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value) {
	EnvironmentMap::iterator item;

	item = this->environment.find(key);
	if(item == this->environment.end()) {
		if(value != Application::Null) {
			this->environment.insert({key, value});
		}
	} else {
		if(value != Application::Null) {
			item->second = value;
		} else {
			this->environment.erase(item);
		}
	}
}


void Application::delEnv(const etl::string<GLOBAL_KEY_SIZE>& key) {
	this->environment.erase(key);
}


bool Application::hasSetting(const etl::string<GLOBAL_KEY_SIZE>& key) {
	return this->settings.find(key) != this->settings.end();
}


const etl::string<GLOBAL_VALUE_SIZE>& Application::getSetting(const etl::string<GLOBAL_KEY_SIZE>& key) {
	SettingsMap::iterator item;

	item = this->settings.find(key);
	if(item == this->settings.end()) {
		return Application::Null;
	}
	return item->second;
}


void Application::setSetting(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value) {
	SettingsMap::iterator item;

	item = this->settings.find(key);
	if(item == this->settings.end()) {
		if(value != Application::Null) {
			this->settings.insert({key, value});
		}
	} else {
		if(value != Application::Null) {
			item->second = value;
		} else {
			this->settings.erase(item);
		}
	}
}


void Application::delSetting(const etl::string<GLOBAL_KEY_SIZE>& key) {
	this->settings.erase(key);
}


void Application::addConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	JsonObject current;

	if(g_system_application.getRunlevel() != RunlevelConfiguring) {
		static etl::string<GLOBAL_VALUE_SIZE> log_message;

		log_message  = "Application::addConfiguration() called in unexpected system-runlevel: ";
		log_message += g_system_application.getRunlevelName();
		log_message += " (only valid in 'configuring')";
		g_util_webserial.send("syslog/warn", log_message);
		return;
	}
	if(command.empty() == true) {
		g_util_webserial.send("syslog/warn", "imcompatible (old) frontend running on linux, as it sent an empty command for end-of-configuration ," \
		                                     "this has been deprecated (for backwards-compatibility, runlevel is now set to 'ready'); " \
		                                     "please upgrade hal9000-frontend (and others?)");
		g_system_application.setRunlevel(RunlevelReady);
		return;
	}
	if(g_util_webserial.hasCommand(command) == false) {
		static etl::string<GLOBAL_VALUE_SIZE> log_message;

		log_message  = "Application::addConfiguration() called with unsupported command '";
		log_message += command;
		log_message += "', please investigate your hal9000-frontend configuration (frontend.ini)";
		g_util_webserial.send("syslog/warn", log_message);
		return;
	}
	current = g_system_application.configuration.createNestedObject();
	current["command"] = command;
	current["data"] = data;
}


bool Application::loadConfiguration() {
	File file;

	this->configuration.clear();
	if(LittleFS.exists("/system/configuration.json") == false) {
		this->processError("warn", "215", "Application error", "system configuration file not found: '(littlefs:)/system/configuration.json'");
		return false;
	}
	file = LittleFS.open("/system/configuration.json", "r");
	if(static_cast<bool>(file) == false) {
		this->processError("panic", "212", "Filesystem error", "failed to open *supposedly existing* '(littlefs:)/system/configuration.json' in " \
		                                                       "read-mode (probably need to reflash littlefs)");
		return false;
	}
	if(deserializeJson(this->configuration, file) != DeserializationError::Ok) {
		this->processError("panic", "215", "Application error", "INI syntax error in (littlefs:)" \
		                                   "'/system/configuration.json'");
		this->configuration.clear();
		file.close();
		return false;
	}
	g_util_webserial.send("syslog/debug", "system configuration loaded from (littlefs:)'/system/configuration.json'");
	return true;
}


bool Application::applyConfiguration() {
	if(this->configuration.size() == 0) {
		if(this->loadConfiguration() == false) {
			return false;
		}
	}
	if(this->configuration.size() > 0) {
		g_util_webserial.send("syslog/debug", "activating application configuration...");
		for(JsonObject item : this->configuration.as<JsonArray>()) {
			if(item.containsKey("command") == true && item.containsKey("data") == true) {
				g_util_webserial.handle(item["command"].as<const char*>(), item["data"].as<JsonVariant>());
			}
		}
		this->configuration.clear();
		g_util_webserial.send("syslog/debug", "...application configuration activated");
	}
	return true;
}


void Application::addErrorContext(const etl::string<GLOBAL_VALUE_SIZE>& message) {
	this->error_context.push_back(message);
}


void Application::processError(const etl::string<GLOBAL_KEY_SIZE>& error_level, const etl::string<GLOBAL_KEY_SIZE>& error_id,
                              const etl::string<GLOBAL_VALUE_SIZE>& error_title, const etl::string<GLOBAL_VALUE_SIZE>& error_details) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> webserial_body;
	static etl::string<GLOBAL_VALUE_SIZE>          error_url;
	static etl::string<GLOBAL_KEY_SIZE>            log_topic;
	static etl::string<GLOBAL_VALUE_SIZE>          log_payload;
	static etl::string<GLOBAL_KEY_SIZE>            screen_error_name;

	if(error_level.compare("panic") == 0) {
		g_system_application.setRunlevel(RunlevelPanicing);
	}
	error_url = this->settings["system/error:url/template"];
	if(error_id.empty() == false) {
		size_t url_id_offset;

		url_id_offset = error_url.find("{error_id}");
		if(url_id_offset != error_url.npos) {
			error_url = error_url.replace(url_id_offset, 10, error_id);
		}
	}
	log_topic = "syslog/";
	if(error_level.compare("panic") == 0) {
		log_topic += "critical";
	} else {
		log_topic += error_level;
	}
	log_payload = "ERROR ";
	log_payload += error_id;
	log_payload += ": ";
	log_payload += error_title;
	log_payload += " => ";
	log_payload += error_details;
	g_util_webserial.send(log_topic, log_payload);

	webserial_body.clear();
	webserial_body["error"] = JsonObject();
	webserial_body["error"]["level"] = error_level;
	webserial_body["error"]["id"] = error_id;
	webserial_body["error"]["title"] = error_title;
	webserial_body["error"]["details"] = error_details;
	if(this->error_context.empty() == false) {
		for(ErrorContext::const_reverse_iterator iter=this->error_context.rbegin(); iter!=this->error_context.rend(); ++iter) {
			webserial_body["error"]["details"].as<String>().concat(" => ");
			webserial_body["error"]["details"].as<String>().concat(iter->c_str());
		}
		this->error_context.clear();
	}
	webserial_body["error"]["url"] = error_url;
	g_util_webserial.send("system/error", webserial_body);

	this->setEnv("gui/screen:error/id", error_id);
	this->setEnv("gui/screen:error/title", error_title);
	this->setEnv("gui/screen:error/url", error_url);
	screen_error_name  = "error:";
	screen_error_name += error_id;
	gui_screen_set(screen_error_name, gui_screen_error);
//TODO:send screen response
	gui_overlay_set("none", gui_overlay_none);
//TODO:send overlay response
}

