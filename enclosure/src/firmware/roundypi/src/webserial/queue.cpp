#include <SimpleWebSerial.h>
#include <RingBuf.h>
#include <pico/mutex.h> 

#include "webserial/queue.h"
#include "globals.h"


WebSerialQueue::WebSerialQueue() {
	mutex_init(&this->mutex);
}

bool WebSerialQueue::pushMessage(String topic, String data) {
	JSONVar json(data);

	return this->pushMessage(topic, json);
}


bool WebSerialQueue::pushMessage(String topic, JSONVar& data) {
	bool  result = false;

	mutex_enter_blocking(&this->mutex);
	if(!this->isFull()) {
		WebSerialMessage  message;

		message.topic = topic;
		message.data = data;
		result = RingBuf::push(message);
	}
	mutex_exit(&this->mutex);
	return result;
}


bool WebSerialQueue::sendMessages() {
	bool result = false;

	if(mutex_try_enter(&this->mutex, NULL)) {
		while(!this->isEmpty()) {
			WebSerialMessage message;

			if(RingBuf::pop(message)) {
				if(message.topic.length() > 0) {
					g_webserial.send(message.topic.c_str(), message.data);
				} else {
					g_webserial.warn(message.data);
				}
			}
		}
		mutex_exit(&this->mutex);
	}
	return result;
}

