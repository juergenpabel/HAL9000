#ifndef __ROUNDYPI_UTIL_JSON_H__
#define __ROUNDYPI_UTIL_JSON_H__

#include <etl/string.h>
#include <ArduinoJson.h>


class JSON : public StaticJsonDocument<UTIL_JSON_FILESIZE_MAX> {
	public:
		JSON();

		bool load(const etl::string<GLOBAL_FILENAME_SIZE>& filename);

		etl::string<GLOBAL_VALUE_SIZE> getString(const etl::string<GLOBAL_KEY_SIZE>& key);
		uint32_t                       getNumber(const etl::string<GLOBAL_KEY_SIZE>& key);
};

#endif

