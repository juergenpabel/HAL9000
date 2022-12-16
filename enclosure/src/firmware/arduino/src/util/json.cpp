#include <LittleFS.h>

#include "globals.h"
#include "json.h"


JSON::JSON() {
}


bool JSON::load(const etl::string<GLOBAL_FILENAME_SIZE>& filename) {
	File  file;

	file = LittleFS.open(filename.c_str(), "r");
	if(file == false) {
		g_util_webserial.send("syslog/warn", "JSON::load(): file not found");
		g_util_webserial.send("syslog/warn", filename);
		return false;
	}
	if(deserializeJson(*this, file) != DeserializationError::Ok) {
		g_util_webserial.send("syslog/warn", "JSON::load(): invalid JSON");
		g_util_webserial.send("syslog/warn", filename);
		file.close();
		return false;
	}
	file.close();
	return true;
}


etl::string<GLOBAL_VALUE_SIZE> JSON::getString(const etl::string<GLOBAL_KEY_SIZE>& key) {
	return (*this)[key.c_str()].as<const char*>();
}


uint32_t JSON::getNumber(const etl::string<GLOBAL_KEY_SIZE>& key) {
	return (*this)[key.c_str()].as<unsigned long>();
}

