#ifndef __APPLICATION_ERROR_H__
#define __APPLICATION_ERROR_H__

#include <etl/string.h>
#include <etl/queue.h>

#ifndef ESP32
extern "C" {
#endif
void setup();
void loop();
#ifndef ESP32
}
#endif
class Application;


class Error {
	protected:
		etl::string<GLOBAL_KEY_SIZE>   level;
		etl::string<GLOBAL_KEY_SIZE>   id;
		etl::string<GLOBAL_VALUE_SIZE> message;
		etl::string<GLOBAL_KEY_SIZE>   detail;
	public:
		Error(const etl::string<GLOBAL_KEY_SIZE>& level, const etl::string<GLOBAL_KEY_SIZE>& id, 
		      const etl::string<GLOBAL_VALUE_SIZE>& message, const etl::string<GLOBAL_VALUE_SIZE>& detail);
		static etl::string<GLOBAL_VALUE_SIZE>& calculateURL(const etl::string<GLOBAL_KEY_SIZE>& id);

	friend class Application;
	friend void setup();
	friend void loop();
};


typedef etl::queue<Error, APPLICATION_ERROR_MAX> ErrorQueue;

#endif

