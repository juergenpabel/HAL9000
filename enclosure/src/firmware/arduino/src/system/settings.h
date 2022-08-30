#ifndef __ROUNDYPI_SYSTEM_SETTINGS_H__
#define __ROUNDYPI_SYSTEM_SETTINGS_H__

#include <string>
#include <map>


class Settings : public std::map<std::string, std::string> {
	public:
		Settings();

		bool load(const char* filename);
		bool save(const char* filename);
};

#endif

