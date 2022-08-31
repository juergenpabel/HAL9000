#include <BSONPP.h>
#include <LittleFS.h>
#include "system/settings.h"


static uint8_t  bson_buffer[SETTINGS_SIZE];

#define QUOTE(value) #value
#define STRING(value) QUOTE(value)

Settings::Settings(std::string filename) {
	this->filename = filename;
	(*this)["system/state:time/sleep"] = STRING(SYSTEM_SETTINGS_TIME_SLEEP);
	(*this)["system/state:time/wakeup"] = STRING(SYSTEM_SETTINGS_TIME_WAKEUP);
	(*this)["system/arduino:loop/sleep_ms"] = STRING(SYSTEM_SETTINGS_LOOP_MS);
	(*this)["device/mcp23X17:i2c/address"] = STRING(SYSTEM_SETTINGS_MCP23X17_ADDRESS);
	(*this)["device/mcp23X17:i2c/pin-sda"] = STRING(SYSTEM_SETTINGS_MCP23X17_PIN_SDA);
	(*this)["device/mcp23X17:i2c/pin-scl"] = STRING(SYSTEM_SETTINGS_MCP23X17_PIN_SCL);
	(*this)["device/mcp23X17:i2c/pin-int_a"] = STRING(SYSTEM_SETTINGS_MCP23X17_PIN_INTA);
	(*this)["device/mcp23X17:i2c/pin-int_b"] = STRING(SYSTEM_SETTINGS_MCP23X17_PIN_INTB);
}


bool Settings::load() {
	bool   result = false;
	File   file;

	file = LittleFS.open(this->filename.c_str(), "r");
	if(file) {
		file.read(bson_buffer, sizeof(bson_buffer));
		file.close();
		result = true;
	}
	if(result) {
		BSONPP   bson(bson_buffer, sizeof(bson_buffer), false);
		int32_t  count = 0;
		char*    key = NULL;
		char*    value = NULL;

		this->clear();
		bson.getKeyCount(&count);
		for(uint32_t i=0; i<count; i++) {
			bson.getKeyAt(i, &key);
			if(key != NULL) {
				bson.get(key, &value);
				if(value != NULL) {
					this->insert({key, value});
				}
			}
		}
	}
	return result;
}


bool Settings::save() {
	bool    result = false;
	File    file;
	BSONPP  bson(bson_buffer, sizeof(bson_buffer));

	auto iter = this->begin();
	while(iter != this->end()) {
		bson.append(iter->first.c_str(), iter->second.c_str());
		++iter;
	}
	file = LittleFS.open(this->filename.c_str(), "w");
	if(file) {
		file.seek(0);
		file.truncate(0);
		file.write(bson.getBuffer(), bson.getSize());
		file.close();
		result = true;
	}
	return result;
}


bool Settings::reset() {
	*this = Settings(this->filename);
	return LittleFS.remove(this->filename.c_str());
}

