#ifndef __ROUNDYPI_SYSTEM_SETTINGS_H__
#define __ROUNDYPI_SYSTEM_SETTINGS_H__

#include <string>
#include <map>


class Settings : public std::map<std::string, std::string> {
	private:
		std::string filename;
	public:
		Settings(std::string filename);

		bool load();
		bool save();
		bool reset();
};

#endif

