#ifndef __ROUNDYPI_SYSTEM_SETTINGS_H__
#define __ROUNDYPI_SYSTEM_SETTINGS_H__

#include <string.h>
#include <map>


class Settings : public std::map<String, String> {
	public:
		Settings();

		bool load(const char* filename);
		bool save(const char* filename);
};

#endif

