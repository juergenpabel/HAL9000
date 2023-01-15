#ifndef __APPLICATION_ERROR_H__
#define __APPLICATION_ERROR_H__

#include <etl/string.h>
#include <etl/queue.h>


class Application;

class Error {
	protected:
		etl::string<GLOBAL_KEY_SIZE>   level;
		etl::string<GLOBAL_KEY_SIZE>   code;
		etl::string<GLOBAL_VALUE_SIZE> message;
		uint16_t                       timeout;
	public:
		Error(const etl::string<GLOBAL_KEY_SIZE>& level, const etl::string<GLOBAL_KEY_SIZE>& code, const etl::string<GLOBAL_KEY_SIZE>& message, uint16_t timeout);
	friend class Application;
};


typedef etl::queue<Error, APPLICATION_ERROR_MAX> ErrorQueue;

#endif

