#ifndef __ROUNDYPI_SYSTEM_SETTINGS_H__
#define __ROUNDYPI_SYSTEM_SETTINGS_H__

#include <etl/string.h>
#include <etl/map.h>


class Settings : public etl::map<etl::string<GLOBAL_KEY_SIZE>, etl::string<GLOBAL_VALUE_SIZE>, SYSTEM_SETTINGS_MAX> {
	private:
		etl::string<GLOBAL_FILENAME_SIZE> filename;
	public:
		Settings(const etl::string<GLOBAL_FILENAME_SIZE>& filename);

		bool load();
		bool save();
		bool reset();
};

#endif

