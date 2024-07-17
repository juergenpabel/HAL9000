#include <etl/string.h>
#include <ArduinoJson.h>

#include "util/webserial.h"
#include "globals.h"


WebSerial::WebSerial() {
}


void WebSerial::begin() {
	g_device_microcontroller.mutex_create("webserial::set", false);
	g_device_microcontroller.mutex_create("webserial::send", false);
	g_device_microcontroller.mutex_create("webserial::update", false);
}


void WebSerial::send(const etl::string<GLOBAL_KEY_SIZE>& command, const etl::string<GLOBAL_VALUE_SIZE>& data, bool data_stringify) {
	static etl::string<GLOBAL_VALUE_SIZE> message;

	g_device_microcontroller.mutex_enter("webserial::send");
	message.clear();
	message  = "[\"";
	message += command;
	message += "\", ";
	if(data_stringify == true) {
		static etl::string<GLOBAL_VALUE_SIZE> data_stringified;
		       size_t pos = 0;

		data_stringified = data;
		pos = data_stringified.find('"', pos);
		while(pos != data_stringified.npos) {
			data_stringified.replace(pos, 1, "\\\"");
			pos = data_stringified.find('"', pos+2);
		}
		message += "\"";
		message += data_stringified;
		message += "\"";
	} else {
		message += data;
	}
	message += "]";

	if(Serial == false) {
		this->queue_send.push(message);
		g_device_microcontroller.mutex_exit("webserial::send");
		return;
	}
	if(this->queue_send.size() > 0) {
		g_device_microcontroller.mutex_enter("Serial");
		while(this->queue_send.empty() == false) {
			Serial.write(this->queue_send.front().c_str());
			Serial.write('\n');
			Serial.flush();
			this->queue_send.pop();
		}
		g_device_microcontroller.mutex_exit("Serial");
	}
	g_device_microcontroller.mutex_enter("Serial");
	Serial.write(message.c_str());
	Serial.write('\n');
	Serial.flush();
	g_device_microcontroller.mutex_exit("Serial");
	g_device_microcontroller.mutex_exit("webserial::send");
}


void WebSerial::send(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& json) {
	static char data[GLOBAL_VALUE_SIZE] = {0};

	serializeJson(json, data);
	this->send(command, data, false);
}


void WebSerial::update() {
	static char   serial_buffer[GLOBAL_VALUE_SIZE] = {0};
	static size_t serial_buffer_pos = 0;

	if(Serial == false) {
		//TODO: set env error code
		//TODOgui_set_screen(gui_screen_error);
		return;
	}
	if(g_device_microcontroller.mutex_try_enter("webserial::update") == true) {
		size_t        serial_available = 0;

		serial_available = Serial.available();
		while(serial_available > 0) {
			g_device_microcontroller.mutex_enter("Serial");
			serial_buffer_pos += Serial.readBytes(&serial_buffer[serial_buffer_pos], min(serial_available, GLOBAL_VALUE_SIZE-serial_buffer_pos-1));
			g_device_microcontroller.mutex_exit("Serial");
			serial_buffer[serial_buffer_pos] = '\0';
			if(serial_buffer_pos > 0) {
				static etl::string<GLOBAL_VALUE_SIZE> serial_input;
				       size_t                         serial_input_pos = 0;

				serial_input = serial_buffer;
				serial_input_pos = serial_input.find('\n');
				while(serial_input_pos != serial_input.npos) {
					static etl::string<GLOBAL_VALUE_SIZE> line;

					line = serial_input.substr(0, serial_input_pos);
					serial_input = serial_input.substr(serial_input_pos+1);
					strncpy(serial_buffer, serial_input.c_str(), sizeof(serial_buffer)-1);
					serial_buffer_pos -= serial_input_pos+1;
					if(line.size() > 0) {
						this->queue_recv.push(line);
					}
					serial_input_pos = serial_input.find('\n');
				}
			}
			serial_available = Serial.available();
		}
		while(this->queue_recv.empty() == false) {
			this->handle(this->queue_recv.front());
			this->queue_recv.pop();
		}
		g_device_microcontroller.mutex_exit("webserial::update");
	}
}


void WebSerial::handle(const etl::string<GLOBAL_VALUE_SIZE>& line) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

	json.clear();
	if(deserializeJson(json, line.c_str()) != DeserializationError::Ok) {
		this->send("syslog/error", "JSON parse of received line failed:");
		this->send("syslog/error", line);
	}
	if(json.is<JsonArray>() && json.size() == 2) {
		this->handle(json[0].as<const char*>(), json[1].as<JsonVariant>());
	} else {
		this->send("syslog/error", "JSON parse of received line returned unexpected JSON object:");
		this->send("syslog/error", line);
	}
}


void WebSerial::handle(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	etl::string<GLOBAL_KEY_SIZE> lookup;

	lookup = command;
	if(this->commands.count(lookup) == 0) {
		lookup = "*";
	}
	if(this->commands.count(lookup) == 1) {
		webserial_command_func handler;

		handler = this->commands[lookup];
		if(handler != nullptr) {
			handler(command, data);
		}
	}
}


void WebSerial::setCommand(const etl::string<GLOBAL_KEY_SIZE>& command, webserial_command_func handler) {
	g_device_microcontroller.mutex_enter("webserial::set");
	if(handler != nullptr) {
		this->commands[command] = handler;
	} else {
		this->commands.erase(command);
	}
	g_device_microcontroller.mutex_exit("webserial::set");
}

