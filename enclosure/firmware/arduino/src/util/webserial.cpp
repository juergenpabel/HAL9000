#include <Arduino.h>
#include <etl/string.h>
#include <ArduinoJson.h>

#include "util/webserial.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/screen/panic/screen.h"
#include "gui/screen/animations/screen.h"
#include "globals.h"


template<const size_t VSize>
WebSerialQueue<VSize>::WebSerialQueue(const etl::string<GLOBAL_KEY_SIZE> name)
                      : etl::queue_lockable<etl::string<WEBSERIAL_LINE_SIZE>, VSize, etl::memory_model::MEMORY_MODEL_SMALL>()
                      , mutex_name(name) {
	g_device_microcontroller.mutex_create(this->mutex_name);
}


template<const size_t VSize>
void WebSerialQueue<VSize>::lock() const {
	g_device_microcontroller.mutex_enter(this->mutex_name);
}


template<const size_t VSize>
void WebSerialQueue<VSize>::unlock() const {
	g_device_microcontroller.mutex_leave(this->mutex_name);
}


WebSerial::WebSerial()
          : commands()
          , queue_recv("webserial_recv")
          , queue_send("webserial_send")
          , millis_begin(0)
          , millis_heartbeatRX(0)
          , millis_heartbeatTX(0) {
}


void WebSerial::begin() {
	Serial.begin(115200);
	if(UTIL_WEBSERIAL_HEARTBEAT_MS > 0) {
		this->millis_begin = millis();
		this->millis_heartbeatRX = this->millis_begin;
		this->millis_heartbeatTX = this->millis_begin;
	}
}


void WebSerial::heartbeat() {
	if(UTIL_WEBSERIAL_HEARTBEAT_MS > 0) {
		if(static_cast<bool>(Serial) == true) {
			unsigned long now;

			now = millis();
			if(now >= (this->millis_heartbeatTX + UTIL_WEBSERIAL_HEARTBEAT_MS)) {
				this->send("ping", "", true, true);
				this->millis_heartbeatTX = now;
			}
		}
	}
}


bool WebSerial::wasAlive() {
	return (this->millis_heartbeatRX > this->millis_begin);
}


bool WebSerial::isAlive() {
	unsigned long now;

	now = millis();
	if(static_cast<bool>(Serial) == true) {
		if(UTIL_WEBSERIAL_HEARTBEAT_MS == 0) {
			return true;
		}
		if(this->wasAlive() == true && now < (this->millis_heartbeatRX + (UTIL_WEBSERIAL_HEARTBEAT_MS*2+500L))) {
			return true;
		}
		if(g_system_application.getRunlevel() > RunlevelRunning) {
			return true;
		}
		if(Serial.available() > 0) {
			return true;
		}
	}
	return false;
}


void WebSerial::send(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& json, bool priority) {
	char payload[GLOBAL_VALUE_SIZE] = {0};

	serializeJson(json, payload);
	this->send(command, payload, priority);
}


void WebSerial::send(const etl::string<GLOBAL_KEY_SIZE>& command, const etl::string<GLOBAL_VALUE_SIZE>& data, bool data_stringify, bool priority) {
	static etl::string<WEBSERIAL_LINE_SIZE> line;
	static etl::string<GLOBAL_VALUE_SIZE>   data_stringified;

	line.clear();
	line  = "[\"";
	line += command;
	line += "\", ";
	if(data_stringify == true) {
		size_t pos = 0;

		data_stringified.clear();
		data_stringified = data;
		pos = data_stringified.find('"', pos);
		while(pos != data_stringified.npos) {
			data_stringified.replace(pos, 1, "\\\"");
			pos = data_stringified.find('"', pos+2);
		}
		line += "\"";
		line += data_stringified;
		line += "\"";
	} else {
		line += data;
	}
	line += "]";

	priority |= this->queue_send.full();
	if(priority == true) {
		Serial.write(line.c_str());
		Serial.write('\n');
		Serial.flush();
	} else {
		if(this->queue_send.push(line) == false) {
			Serial.write("[\"syslog/warn\", \"send queue full in Webserial::send(), sending out-of-order:\"]\n");
			Serial.write(line.c_str());
			Serial.write('\n');
			Serial.flush();
		}
	}
}


void WebSerial::update() {
	static unsigned long millis_connection_timeout = 0;
	static char          receive_buffer[WEBSERIAL_LINE_SIZE] = {0};
	static size_t        receive_buffer_pos = 0;
	       size_t        serial_available = 0;
	       etl::string<WEBSERIAL_LINE_SIZE> webserial_recv_line;
	       etl::string<WEBSERIAL_LINE_SIZE> webserial_send_line;

	if(g_system_application.getRunlevel() != RunlevelPanicing) {
		this->heartbeat();
		switch(this->isAlive()) {
			case true:
				if(gui_screen_get() == gui_screen_error && gui_screen_getname().compare("error:200") == 0) {
					gui_screen_set("none", gui_screen_none);
				}
				break;
			case false:
				if(this->wasAlive() == false) {
					if(millis_connection_timeout == 0) {
						millis_connection_timeout = this->millis_begin;
						if(g_system_application.hasSetting("system/webserial:connection/timeout") == true) {
							millis_connection_timeout += atol(g_system_application.getSetting("system/webserial:connection/timeout").c_str());
						} else {
							millis_connection_timeout += UTIL_WEBSERIAL_CONNECTION_TIMEOUT_MS;
						}
					}
					if(millis_connection_timeout > this->millis_begin && millis() > millis_connection_timeout) {
						g_system_application.processError("critical", "200", "No connection to host", "Service 'frontend' didn't connect (USB)");
						millis_connection_timeout = this->millis_begin;
					}
				}
				return;
		}
	}
	while(this->queue_send.size() > 0) {
		if(this->queue_send.pop(webserial_send_line) == true) {
			Serial.write(webserial_send_line.c_str());
			Serial.write('\n');
			Serial.flush();
		}
	}
	while(this->queue_recv.size() > 0) {
		if(this->queue_recv.pop(webserial_recv_line) == true) {
			this->handle(webserial_recv_line);
			while(this->queue_send.size() > 0) {
				if(this->queue_send.pop(webserial_send_line) == true) {
					Serial.write(webserial_send_line.c_str());
					Serial.write('\n');
					Serial.flush();
				}
			}
		}
	}

	serial_available = Serial.available();
	while(serial_available > 0 && this->queue_recv.available() > 0) {
		receive_buffer_pos += Serial.readBytes(&receive_buffer[receive_buffer_pos], min(serial_available, WEBSERIAL_LINE_SIZE-receive_buffer_pos-1));
		receive_buffer[receive_buffer_pos] = '\0';
		if(receive_buffer_pos > 0) {
			static etl::string<WEBSERIAL_LINE_SIZE> input_chunk;
			       size_t                           input_chunk_pos = 0;

			input_chunk = receive_buffer;
			input_chunk_pos = input_chunk.find('\n');
			while(input_chunk_pos != input_chunk.npos && this->queue_recv.available() > 0) {
				webserial_recv_line = input_chunk.substr(0, input_chunk_pos);
				if(this->queue_recv.push(webserial_recv_line) != true) {
					Serial.write("[\"syslog/error\", \"recv queue full in Webserial::update(), dropping:\"]\n");
					Serial.write(webserial_recv_line.c_str());
					Serial.write('\n');
					Serial.flush();
				}
				strncpy(receive_buffer, input_chunk.substr(input_chunk_pos+1).c_str(), sizeof(receive_buffer)-1);
				receive_buffer_pos -= input_chunk_pos+1;
				input_chunk = receive_buffer;
				input_chunk_pos = input_chunk.find('\n');
			}
			serial_available = Serial.available();
			if(UTIL_WEBSERIAL_HEARTBEAT_MS > 0 && serial_available == false) {
				this->millis_heartbeatRX = millis();
			}
		}
	}
	while(this->queue_recv.size() > 0) {
		if(this->queue_recv.pop(webserial_recv_line) == true) {
			this->handle(webserial_recv_line);
			while(this->queue_send.size() > 0) {
				if(this->queue_send.pop(webserial_send_line) == true) {
					Serial.write(webserial_send_line.c_str());
					Serial.write('\n');
					Serial.flush();
				}
			}
		}
	}
}


void WebSerial::handle(const etl::string<WEBSERIAL_LINE_SIZE>& line) {
	static StaticJsonDocument<WEBSERIAL_LINE_SIZE*2> json;

	json.clear();
	if(deserializeJson(json, line) != DeserializationError::Ok) {
		this->send("syslog/error", "JSON parse of received line failed:");
		this->send("syslog/error", line);
	}
	if(json.is<JsonArray>() && json.size() == 2) {
		if(json[0] == String("ping")) {
			this->send("pong", "");
			return;
		}
		if(json[0] == String("pong")) {
			return;
		}
		this->handle(json[0].as<const char*>(), json[1].as<JsonVariant>());
	} else {
		this->send("syslog/error", "JSON parse of received line returned unexpected JSON object:");
		this->send("syslog/error", line);
	}
}


void WebSerial::handle(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	webserial_command_func handler = nullptr;

	if(this->commands.count(command) == 1) {
		handler = this->commands[command];
		if(handler == nullptr) {
			if(this->commands.count("*") == 1) {
				handler = this->commands["*"];
			}
		}
	} else {
		if(command.compare("") == 0) {
			if(this->commands.count("*") == 1) {
				handler = this->commands["*"];
			}
		}
	}
	if(handler != nullptr) {
		handler(command, data);
	}
}


bool WebSerial::addCommand(const etl::string<GLOBAL_KEY_SIZE>& command, webserial_command_func handler) {
	if(command.empty() == true) {
		return false;
	}
	if(this->commands.count(command) != 0) {
		return false;
	}
	this->commands[command] = handler;
	return true;
}


bool WebSerial::delCommand(const etl::string<GLOBAL_KEY_SIZE>& command, webserial_command_func handler) {
	if(command.empty() == true) {
		return false;
	}
	if(this->commands.count(command) != 1) {
		return false;
	}
	if(this->commands[command] != handler) {
		return false;
	}
	this->commands.erase(command);
	return true;
}


bool WebSerial::hasCommand(const etl::string<GLOBAL_KEY_SIZE>& command) {
	if(this->commands.count(command) == 1) {
		return true;
	}
	return false;
}


void WebSerial::clearCommands() {
	this->commands.clear();
}

