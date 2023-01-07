#include <TimeLib.h>

#include "application/environment.h"
#include "application/application.h"


EnvironmentWriter::EnvironmentWriter(Application& application, const etl::string<GLOBAL_KEY_SIZE>& key)
                  :m_application(application)
                  ,m_key(key) {
	this->m_application.m_environment[m_key.c_str()] = "";
}


size_t EnvironmentWriter::write(uint8_t c) {
	this->m_application.m_environment[m_key].append(1, (char)c);
	return 1;
}


size_t EnvironmentWriter::write(const uint8_t *buffer, size_t length) {
	this->m_application.m_environment[m_key].append((const char*)buffer, length);
	return length;
}

