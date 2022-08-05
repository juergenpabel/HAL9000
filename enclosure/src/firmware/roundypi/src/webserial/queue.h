#ifndef __ROUNDYPI_WEBSERIAL_QUEUE_H__
#define __ROUNDYPI_WEBSERIAL_QUEUE_H__

#include <string.h>
#include <JSONVar.h>
#include <RingBuf.h>


typedef struct {
	String   topic;
	JSONVar  data;
} WebSerialMessage;


class WebSerialQueue : public RingBuf<WebSerialMessage, RingBufSize> {
	private:
		mutex_t mutex;
	public:
		WebSerialQueue();
		bool pushMessage(String topic, JSONVar& data);
		bool pushMessage(String topic, String data);
		bool sendMessages();
};

#endif

