#include <TimeLib.h>

#include "application/environment.h"
#include "application/application.h"


EnvironmentWriter::EnvironmentWriter(Application& application, const etl::string<GLOBAL_KEY_SIZE>& key)
                  :application(application)
                  ,key(key) {
	this->application.environment[key] = "";
}


size_t EnvironmentWriter::write(uint8_t c) {
	this->application.environment[key].append(1, (char)c);
	return 1;
}


size_t EnvironmentWriter::write(const uint8_t *buffer, size_t length) {
	this->application.environment[key].append((const char*)buffer, length);
	return length;
}

