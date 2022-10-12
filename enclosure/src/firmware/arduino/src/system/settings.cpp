#include <LittleFS.h>
#include <etl/string.h>

#include "system/settings.h"
#include "globals.h"

#define LINE_SIZE (GLOBAL_KEY_SIZE + 1 + GLOBAL_VALUE_SIZE + 1)

typedef etl::string<UTIL_WEBSERIAL_BODY_SIZE> LogString;


Settings::Settings(const etl::string<GLOBAL_FILENAME_SIZE>& filename) {
	this->filename = filename;
}


bool Settings::load() {
	File                      file;
	char                      line_buffer[LINE_SIZE+1] = {0};
        int                       line_buffer_pos = 0;
	etl::string<LINE_SIZE+1>  line;
	size_t                    line_sep_pos = 0;
	size_t                    line_end_pos = 0;

	this->clear();
	file = LittleFS.open(this->filename.c_str(), "r");
	if(!file) {
		g_util_webserial.send("syslog/error", LogString("Settings::load('").append(this->filename).append(LogString("') => could not open file")));
		return false;
	}
	if(file.size() == 0) {
		file.close();
		return true;
	}
	do {
		if(file.position() < file.size()) {
			line_buffer_pos += file.read((uint8_t*)&line_buffer[line_buffer_pos], sizeof(line_buffer)-line_buffer_pos-1);
			line_buffer[line_buffer_pos] = '\0';
		}
		line = line_buffer;
		line_end_pos = line.find('\n');
		if(line_end_pos == line.npos) {
			file.close();
			this->clear();
			g_util_webserial.send("syslog/error", LogString("Settings::load('").append(this->filename).append(LogString("') => no newline")));
			return false;
		}
		line_sep_pos = line.find('=');
		if(line_sep_pos != line.npos && line_sep_pos < line_end_pos) {
			etl::string<GLOBAL_KEY_SIZE> key;
			etl::string<GLOBAL_VALUE_SIZE> value;

			key = line.substr(0, line_sep_pos);
			value = line.substr(line_sep_pos+1, line_end_pos-(line_sep_pos+1));
			this->insert({key, value});
		}
		for(uint8_t i=line_end_pos+1; i<line_buffer_pos; i++) {
			line_buffer[i-(line_end_pos+1)] = line_buffer[i];
		}
		line_buffer_pos -= line_end_pos+1;
		line_buffer[line_buffer_pos] = '\0';
	} while(file.position() < file.size() || line_buffer_pos > 0);
	file.close();
	return true;
}


bool Settings::save() {
	File    file;

	LittleFS.remove(this->filename.c_str());
	file = LittleFS.open(this->filename.c_str(), "w");
	if(!file) {
		g_util_webserial.send("syslog/error", LogString("Settings::save('").append(this->filename).append(LogString("') => failed to open file")));
		return false;
	}
	for(Settings::iterator iter=this->begin(); iter!=this->end(); ++iter) {
		file.write((uint8_t*)iter->first.c_str(), iter->first.size());
		file.write((uint8_t*)"=", 1);
		file.write((uint8_t*)iter->second.c_str(), iter->second.size());
		file.write((uint8_t*)"\n", 1);
	}
	file.close();
	return true;
}


bool Settings::reset() {
	this->clear();
	return true;
}

