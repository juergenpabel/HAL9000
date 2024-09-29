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
            ,environment()
            ,settings("/system/application/settings.ini") {
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


void Application::onConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> configuration;
	       JsonObject                                          current;

	switch(g_system_application.getRunlevel()) {
		case RunlevelConfiguring:
			if(command.empty() == false) { // non-empty line means configuration instruction
				if(g_util_webserial.hasCommand(command) == true) {
					current = configuration.createNestedObject();
					current["command"] = command;
					current["data"] = data;
				}
			}
			if(command.empty() == true) { // empty line means end-of-configuration
				if(configuration.size() > 0) {
					File file;

					g_util_webserial.send("syslog/debug", "saving application configuration to (littlefs:)" \
					                                      "'/system/application/configuration.json'");
					file = LittleFS.open("/system/application/configuration.json", "w");
					if(static_cast<bool>(file) == true) {
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
				g_system_application.setRunlevel(RunlevelWaiting);
			}
			break;
		case RunlevelWaiting:
			if(configuration.size() == 0) {
				if(LittleFS.exists("/system/application/configuration.json") == true) {
					File file;

					file = LittleFS.open("/system/application/configuration.json", "r");
					if(static_cast<bool>(file) == true) {
						if(deserializeJson(configuration, file) == DeserializationError::Ok) {
							g_util_webserial.send("syslog/debug", "system configuration loaded from (littlefs:)" \
							                                      "'/system/application/configuration.json'");
						} else {
							g_system_application.processError("panic", "215", "Application error", "INI syntax error in (littlefs:)" \
							                                                               "'/system/application/configuration.json'");
							configuration.clear();
						}
						file.close();
					} else {
						g_system_application.processError("panic", "212", "Filesystem error", "failed to open *supposedly existing* (littlefs:)" \
						                                                              "'/system/application/configuration.json' in " \
						                                                              "read-mode (probably need to reflash littlefs)");
					}
				} else {
					g_system_application.processError("warn", "215", "Application error", "system configuration file not found: " \
					                                                              "(littlefs:)'/system/application/configuration.json'");
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
			etl::string<GLOBAL_VALUE_SIZE> log_message;

			log_message  = "Application::onConfiguration() called in unexpected system-runlevel: ";
			log_message += g_system_application.getRunlevelName();
			g_util_webserial.send("syslog/warn", log_message);
	}
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

	if(error_id.compare("210") != 0) {
		webserial_body.clear();
		webserial_body["error"] = JsonObject();
		webserial_body["error"]["id"] = error_id;
		webserial_body["error"]["level"] = error_level;
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
	}
	this->setEnv("gui/screen:error/id", error_id);
	this->setEnv("gui/screen:error/title", error_title);
	this->setEnv("gui/screen:error/url", error_url);
	screen_error_name  = "error:";
	screen_error_name += error_id;
	gui_screen_set(screen_error_name, gui_screen_error);
	gui_overlay_set("none", gui_overlay_none);
}

