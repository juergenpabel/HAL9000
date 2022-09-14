#include <pico/mutex.h> 
#include <etl/string.h>
#include <ArduinoJson.h>
#include "util/webserial.h"



WebSerial::WebSerial() {
	recursive_mutex_init(&this->serial_mutex);
}


void WebSerial::send(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, const etl::string<UTIL_WEBSERIAL_BODY_SIZE>& body) {
	etl::string<UTIL_WEBSERIAL_LINE_SIZE> message;

	message = "[\"";
	message += topic;
	message += "\", ";
	message += body;
	message += "]";
	if(Serial == false || recursive_mutex_try_enter(&this->serial_mutex, NULL) == false) {
		this->queue_send.push(message);
		return;
	}
	Serial.write(message.c_str());
	Serial.write('\n');
	recursive_mutex_exit(&this->serial_mutex);
}


void WebSerial::send(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, const JsonVariant& data) {
	char body[UTIL_WEBSERIAL_BODY_SIZE] = {0};

	serializeJson(data, body);
	this->send(topic, body);
}


void WebSerial::update() {
	static char                                  serial_buffer[UTIL_WEBSERIAL_LINE_SIZE] = {0};
	static etl::string<UTIL_WEBSERIAL_LINE_SIZE> serial_input;
	static size_t                                serial_input_pos = 0;

	if(Serial) {
		if(this->queue_send.size() > 0) {
			recursive_mutex_enter_blocking(&this->serial_mutex);

			while(this->queue_send.empty() == false) {
				Serial.write(this->queue_send.front().c_str());
				Serial.write('\n');
				this->queue_send.pop();
			}
			recursive_mutex_exit(&this->serial_mutex);
		}

		int serial_available = Serial.available();
		if(serial_available > 0) {
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
							if(handler != NULL) {
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
		recursive_mutex_exit(&this->serial_mutex);
	}
}


void WebSerial::set(const etl::string<UTIL_WEBSERIAL_TOPIC_SIZE>& topic, webserial_command_func handler) {
	if(handler != nullptr) {
		this->commands[topic] = handler;
	} else {
		this->commands.erase(topic);
	}
}

