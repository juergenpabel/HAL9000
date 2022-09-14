#include <BSONPP.h>
#include <LittleFS.h>
#include "system/settings.h"

#define SYSTEM_SETTINGS_SIZE 2048
static uint8_t  bson_buffer[SYSTEM_SETTINGS_SIZE];

#define QUOTE(value) #value
#define STRING(value) QUOTE(value)

Settings::Settings(const etl::string<GLOBAL_FILENAME_SIZE>& filename) {
	this->filename = filename;
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
		for(int32_t i=0; i<count; i++) {
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
	BSONPP  bson(bson_buffer, sizeof(bson_buffer), true);
	File    file;

	for(Settings::iterator iter=this->begin(); iter!=this->end(); ++iter) {
		bson.append(iter->first.c_str(), iter->second.c_str());
	}
	file = LittleFS.open(this->filename.c_str(), "w");
	if(file) {
		file.seek(0);
		file.truncate(0);
		file.write(bson.getBuffer(), bson.getBufferSize());
		file.close();
		result = true;
	}
	return result;
}


bool Settings::reset() {
	*this = Settings(this->filename);
	LittleFS.remove(this->filename.c_str());
	return true;
}

