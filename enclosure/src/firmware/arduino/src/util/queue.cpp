#include <SimpleWebSerial.h>
#include <pico/mutex.h> 

#include "util/queue.h"
#include "globals.h"


WebSerialQueue::WebSerialQueue() {
	mutex_init(&this->mutex);
}


void WebSerialQueue::pushMessage(std::string topic, arduino::String data) {
	JSONVar json(data);

	this->pushMessage(topic, json);
}


void WebSerialQueue::pushMessage(std::string topic, JSONVar& data) {
	WebSerialMessage  message;

	message.topic = topic;
	message.data = data;
	mutex_enter_blocking(&this->mutex);
	queue.push(message);
	mutex_exit(&this->mutex);
}


void WebSerialQueue::sendMessages() {
	if(mutex_try_enter(&this->mutex, NULL)) {
		while(this->queue.empty() == false) {
			WebSerialMessage message;

			message = this->queue.front();
			this->queue.pop();
			if(message.topic.length() > 0) {
				g_util_webserial.send(message.topic.c_str(), message.data);
			} else {
				g_util_webserial.send("syslog", message.data);
			}
		}
		mutex_exit(&this->mutex);
	}
}


void WebSerialQueue::dropMessages() {
	if(mutex_try_enter(&this->mutex, NULL)) {
		while(this->queue.empty() == false) {
			this->queue.pop();
		}
		mutex_exit(&this->mutex);
	}
}

