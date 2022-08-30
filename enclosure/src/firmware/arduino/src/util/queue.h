#ifndef __ROUNDYPI_WEBSERIAL_QUEUE_H__
#define __ROUNDYPI_WEBSERIAL_QUEUE_H__

#include <string>
#include <queue>
#include <JSONVar.h>


typedef struct {
	std::string  topic;
	JSONVar      data;
} WebSerialMessage;


class WebSerialQueue {
	private:
		std::queue<WebSerialMessage> queue;
		mutex_t mutex;
	public:
		WebSerialQueue();
		void pushMessage(std::string topic, JSONVar& data);
		void pushMessage(std::string topic, arduino::String data);
		void sendMessages();
};

#endif

