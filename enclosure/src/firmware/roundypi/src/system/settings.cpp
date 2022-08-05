#include <BSONPP.h>
#include <LittleFS.h>
#include "system/settings.h"


static uint8_t  bson_buffer[SETTINGS_SIZE];


Settings::Settings() {
}


bool Settings::load(const char* filename) {
	bool   result = false;
	File   file;

	file = LittleFS.open(filename, "r");
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


bool Settings::save(const char* filename) {
	bool    result = false;
	File    file;
	BSONPP  bson(bson_buffer, sizeof(bson_buffer));

	auto iter = this->begin();
	while(iter != this->end()) {
		bson.append(iter->first.c_str(), iter->second.c_str());
		++iter;
	}
	file = LittleFS.open(filename, "w");
	if(file) {
		file.seek(0);
		file.truncate(0);
		file.write(bson.getBuffer(), bson.getSize());
		file.close();
		result = true;
	}
	return result;
}

