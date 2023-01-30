#ifndef __APPLICATION_SETTINGS_H__
#define __APPLICATION_SETTINGS_H__

#include <etl/string.h>
#include <etl/map.h>

typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, etl::string<GLOBAL_VALUE_SIZE>, APPLICATION_SETTINGS_MAX> SettingsMap;


class Settings : public SettingsMap {
	private:
		etl::string<GLOBAL_FILENAME_SIZE> filename;
	public:
		Settings(const etl::string<GLOBAL_FILENAME_SIZE>& filename);

		bool load();
		bool save();
		bool reset();
};

#endif

