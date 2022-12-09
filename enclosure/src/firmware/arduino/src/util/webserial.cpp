#include <etl/string.h>
#include <ArduinoJson.h>

#include "util/webserial.h"
#include "system/runtime.h"
#include "globals.h"


WebSerial::WebSerial() {
}


void WebSerial::begin() {
	g_device_microcontroller.mutex_create("webserial::set", false);
	g_device_microcontroller.mutex_create("webserial::send", false);
	g_device_microcontroller.mutex_create("webserial::update", false);
}


void WebSerial::send(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, const etl::string<UTIL_WEBSERIAL_DATA_SIZE>& data, bool data_stringify) {
	static etl::string<UTIL_WEBSERIAL_LINE_SIZE> message;

	g_device_microcontroller.mutex_enter("webserial::send");
	message = "[\"";
	message += topic;
	message += "\", ";
	if(data_stringify == true) {
		static etl::string<UTIL_WEBSERIAL_DATA_SIZE> data_stringified;
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

	if(Serial == false || g_system_runtime.getStatus() == StatusOffline) {
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


void WebSerial::send(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, const JsonVariant& json) {
	char data[UTIL_WEBSERIAL_DATA_SIZE] = {0};

	serializeJson(json, data);
	this->send(topic, data, false);
}


void WebSerial::update() {
	static unsigned long serial_heartbeat_millis = 0;
	static char          serial_buffer[UTIL_WEBSERIAL_LINE_SIZE] = {0};
	static size_t        serial_buffer_pos = 0;

	if(Serial == false) {
		if(g_system_runtime.getStatus() == StatusOnline) {
			g_system_runtime.setStatus(StatusOffline);
		}
		serial_heartbeat_millis = 0;
		return;
	}
	if(g_device_microcontroller.mutex_try_enter("webserial::update") == true) {
		size_t        serial_available = 0;
		unsigned long now = 0;

		now = millis();
		serial_available = Serial.available();
		while(serial_available > 0) {
			g_device_microcontroller.mutex_enter("Serial");
			serial_buffer_pos += Serial.readBytes(&serial_buffer[serial_buffer_pos], min(serial_available, UTIL_WEBSERIAL_LINE_SIZE-serial_buffer_pos-1));
			g_device_microcontroller.mutex_exit("Serial");
			serial_buffer[serial_buffer_pos] = '\0';
			if(serial_buffer_pos > 0) {
				static etl::string<UTIL_WEBSERIAL_LINE_SIZE> serial_input;
				       size_t                                serial_input_pos = 0;

				serial_input = serial_buffer;
				serial_input_pos = serial_input.find('\n');
				while(serial_input_pos != serial_input.npos) {
					static etl::string<UTIL_WEBSERIAL_LINE_SIZE> line;

					line = serial_input.substr(0, serial_input_pos);
					serial_input = serial_input.substr(serial_input_pos+1);
					strncpy(serial_buffer, serial_input.c_str(), sizeof(serial_buffer)-1);
					serial_buffer_pos -= serial_input_pos+1;
					if(line.size() > 0) {
						this->queue_recv.push(line);
					} else {
						serial_heartbeat_millis = now;
					}
					serial_input_pos = serial_input.find('\n');
				}
			}
			serial_available = Serial.available();
		}
		if(now == serial_heartbeat_millis) {
			g_system_runtime.setStatus(StatusOnline);
			g_device_microcontroller.mutex_enter("Serial");
			Serial.write('\n');
			Serial.flush();
			g_device_microcontroller.mutex_exit("Serial");
		}
		if(now > (serial_heartbeat_millis+1000+1000)) {
			if(g_system_runtime.getStatus() == StatusOnline) {
				g_system_runtime.setStatus(StatusOffline);
			}
		}
		while(this->queue_recv.empty() == false) {
			static StaticJsonDocument<1024> message;

			message.clear();
			deserializeJson(message, this->queue_recv.front().c_str());
			if(message.is<JsonArray>() && message.size() == 2) {
				etl::string<UTIL_WEBSERIAL_TOPIC_SIZE> command;

				command = message[0].as<const char*>();
				if(this->commands.count(command) == 1) {
					webserial_command_func handler;

					handler = this->commands[command];
					if(handler != nullptr) {
						JsonVariant data;

						data = message[1].as<JsonVariant>();
						handler(data);
					}
				}
			}
			this->queue_recv.pop();
		}
		g_device_microcontroller.mutex_exit("webserial::update");
	}
}


void WebSerial::set(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, webserial_command_func handler) {
	g_device_microcontroller.mutex_enter("webserial::set");
	if(handler != nullptr) {
		this->commands[topic] = handler;
	} else {
		this->commands.erase(topic);
	}
	g_device_microcontroller.mutex_exit("webserial::set");
}

