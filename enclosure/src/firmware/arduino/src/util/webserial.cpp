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
	g_device_microcontroller.mutex_create("webserial.queue_recv", false);
	g_device_microcontroller.mutex_create("webserial.queue_send", false);
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

	if(Serial == false || g_device_microcontroller.mutex_try_enter("Serial") == false) {
		g_device_microcontroller.mutex_enter("webserial.queue_send");
		this->queue_send.push(message);
		g_device_microcontroller.mutex_exit("webserial.queue_send");
		g_device_microcontroller.mutex_exit("webserial::send");
		return;
	}
	Serial.write(message.c_str());
	Serial.write('\n');
	g_device_microcontroller.mutex_exit("Serial");
	g_device_microcontroller.mutex_exit("webserial::send");
}


void WebSerial::send(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, const JsonVariant& json) {
	char data[UTIL_WEBSERIAL_DATA_SIZE] = {0};

	serializeJson(json, data);
	this->send(topic, data, false);
}


void WebSerial::update() {
	static char                                  serial_buffer[UTIL_WEBSERIAL_LINE_SIZE] = {0};
	static etl::string<UTIL_WEBSERIAL_LINE_SIZE> serial_input;
	static size_t                                serial_input_pos = 0;
	       size_t                                serial_available = 0;

	if(Serial == false) {
		return;
	}
	if(this->queue_send.size() > 0) {
		if(g_device_microcontroller.mutex_try_enter("webserial.queue_send") == true) {
			while(this->queue_send.empty() == false) {
				Serial.write(this->queue_send.front().c_str());
				Serial.write('\n');
				this->queue_send.pop();
			}
			g_device_microcontroller.mutex_exit("webserial.queue_send");
		}
	}
	if(g_device_microcontroller.mutex_try_enter("webserial::update") == true) {
		g_device_microcontroller.mutex_enter("Serial");
		serial_available = Serial.available();
		if(serial_available > 0) {
			if(serial_input_pos == UTIL_WEBSERIAL_LINE_SIZE) {
				this->send("syslog/warn", "WebSerial::update() => line buffer full, no newline (\\n) found: dropping line buffer (data loss)");
				serial_input_pos = 0;
			}
			serial_input_pos += Serial.readBytes(serial_buffer+serial_input_pos, min(serial_available, UTIL_WEBSERIAL_LINE_SIZE-serial_input_pos));
			if(serial_input_pos > 0) {
				size_t pos = 0;

				serial_input = serial_buffer;
				pos = serial_input.find("\n");
				while(pos != serial_input.npos) {
					static StaticJsonDocument<1024> message;
					etl::string<UTIL_WEBSERIAL_LINE_SIZE> line;

					message.clear();
					line = serial_input.substr(0, pos);
					serial_input = serial_input.substr(pos+1);
					strncpy(serial_buffer, serial_input.c_str(), sizeof(serial_buffer)-1);
					serial_input_pos -= pos+1;
					deserializeJson(message, line);
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
					pos = serial_input.find("\n");
				}
			}
		}
		g_device_microcontroller.mutex_exit("Serial");
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

