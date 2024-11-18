#ifndef __SYSTEM_SETTINGS_H__
#define __SYSTEM_SETTINGS_H__

#include <etl/string.h>
#include <etl/map.h>

typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, etl::string<GLOBAL_VALUE_SIZE>, APPLICATION_SETTINGS_MAX> SettingsMap;
class Application;

class Settings : public SettingsMap {
	protected:
		Settings();

		bool load(const etl::string<GLOBAL_FILENAME_SIZE>& filename);
		bool save(const etl::string<GLOBAL_FILENAME_SIZE>& filename);
		bool reset();

	friend class Application;
};

#endif

