#include <Arduino.h>
#include <etl/string.h>
#include <ArduinoJson.h>

#include "util/webserial.h"
#include "gui/screen/screen.h"
#include "gui/screen/animations/screen.h"
#include "gui/screen/error/screen.h"
#include "globals.h"


WebSerial::WebSerial() {
}


void WebSerial::begin() {
	Serial.begin(115200);
	this->queue_recv_handle = xQueueCreateStatic(UTIL_WEBSERIAL_QUEUE_RECV_MAX, WEBSERIAL_LINE_SIZE, this->queue_recv_itemdata, &this->queue_recv_metadata);
	this->queue_send_handle = xQueueCreateStatic(UTIL_WEBSERIAL_QUEUE_SEND_MAX, WEBSERIAL_LINE_SIZE, this->queue_send_itemdata, &this->queue_send_metadata);
}


void WebSerial::send(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& json) {
	char payload[GLOBAL_VALUE_SIZE] = {0};

	serializeJson(json, payload);
	this->send(command, payload, false);
}


void WebSerial::send(const etl::string<GLOBAL_KEY_SIZE>& command, const etl::string<GLOBAL_VALUE_SIZE>& data, bool data_stringify) {
	etl::string<WEBSERIAL_LINE_SIZE> line;

	line  = "[\"";
	line += command;
	line += "\", ";
	if(data_stringify == true) {
		etl::string<GLOBAL_VALUE_SIZE> data_stringified;
		size_t pos = 0;

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

	if(xQueueSend(this->queue_send_handle, line.c_str(), 50) != pdTRUE) {
		Serial.write("[\"syslog/critical\", \"send queue full in Webserial::send(), sending out-of-order:\"]\n");
		Serial.write(line.c_str());
		Serial.write('\n');
		Serial.flush();
	}
}


void WebSerial::update() {
	       char   webserial_send_line[WEBSERIAL_LINE_SIZE];
	       char   webserial_recv_line[WEBSERIAL_LINE_SIZE];
	static char   receive_buffer[WEBSERIAL_LINE_SIZE] = {0};
	static size_t receive_buffer_pos = 0;
	       size_t serial_available = 0;

	if(Serial == false) {
		if(gui_screen_get() != gui_screen_animations && gui_screen_get() != gui_screen_error) {
			Error error("error", "09", "Lost connection to host", "ERROR #09");

			g_util_webserial.send(error.level.insert(0, "syslog/"), error.message); // TODO: + " => " + error.detail);
			g_application.setEnv("gui/screen:error/id", error.id);
			g_application.setEnv("gui/screen:error/message", error.message);
			gui_screen_set("error", gui_screen_error);
		}
		return;
	}
	while(uxQueueMessagesWaiting(this->queue_send_handle) > 0) {
		if(xQueueReceive(this->queue_send_handle, webserial_send_line, 0) == pdTRUE) {
			Serial.write(webserial_send_line);
			Serial.write('\n');
			Serial.flush();
		}
	}
	while(uxQueueMessagesWaiting(this->queue_recv_handle) > 0) {
		if(xQueueReceive(this->queue_recv_handle, webserial_recv_line, 0) == pdTRUE) {
			this->handle(webserial_recv_line);
			while(uxQueueMessagesWaiting(this->queue_send_handle) > 0) {
				if(xQueueReceive(this->queue_send_handle, webserial_send_line, 0) == pdTRUE) {
					Serial.write(webserial_send_line);
					Serial.write('\n');
					Serial.flush();
				}
			}
		}
	}

	serial_available = Serial.available();
	while(serial_available > 0 && uxQueueSpacesAvailable(this->queue_recv_handle) > 0) {
		receive_buffer_pos += Serial.readBytes(&receive_buffer[receive_buffer_pos], min(serial_available, WEBSERIAL_LINE_SIZE-receive_buffer_pos-1));
		receive_buffer[receive_buffer_pos] = '\0';
		if(receive_buffer_pos > 0) {
			static etl::string<WEBSERIAL_LINE_SIZE> input_chunk;
			       size_t                           input_chunk_pos = 0;

			input_chunk = receive_buffer;
			input_chunk_pos = input_chunk.find('\n');
			while(input_chunk_pos != input_chunk.npos && uxQueueSpacesAvailable(this->queue_recv_handle) > 0) {
				memcpy(webserial_recv_line, input_chunk.c_str(), input_chunk_pos);
				webserial_recv_line[input_chunk_pos] = '\0';
				if(xQueueSend(this->queue_recv_handle, webserial_recv_line, 0) != pdTRUE) {
					Serial.write("[\"syslog/critical\", \"recv queue full in Webserial::update(), dropping:\"]\n");
					Serial.write(webserial_recv_line);
					Serial.write('\n');
					Serial.flush();
				}
				strncpy(receive_buffer, input_chunk.substr(input_chunk_pos+1).c_str(), sizeof(receive_buffer)-1);
				receive_buffer_pos -= input_chunk_pos+1;
				input_chunk = receive_buffer;
				input_chunk_pos = input_chunk.find('\n');
			}
			serial_available = Serial.available();
		}
	}
	while(uxQueueMessagesWaiting(this->queue_recv_handle) > 0) {
		if(xQueueReceive(this->queue_recv_handle, webserial_recv_line, 0) == pdTRUE) {
			this->handle(webserial_recv_line);
			while(uxQueueMessagesWaiting(this->queue_send_handle) > 0) {
				if(xQueueReceive(this->queue_send_handle, webserial_send_line, 0) == pdTRUE) {
					Serial.write(webserial_send_line);
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
	static etl::string<GLOBAL_KEY_SIZE> lookup;

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
	if(handler != nullptr) {
		this->commands[command] = handler;
	} else {
		this->commands.erase(command);
	}
}

