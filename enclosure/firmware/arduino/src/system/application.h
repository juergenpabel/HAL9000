#ifndef __SYSTEM_APPLICATION_H__
#define __SYSTEM_APPLICATION_H__

#include <etl/string.h>
#include <etl/map.h>
#include <etl/list.h>
#include <ArduinoJson.h>

#include "system/settings.h"
#include "system/environment.h"

typedef etl::list<etl::string<GLOBAL_VALUE_SIZE>, APPLICATION_ERROR_MAX> ErrorContext;
typedef StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2>              Configuration;

typedef enum {
	RunlevelUnknown      = 0x00,
	RunlevelStarting     = 0x01,
	RunlevelConfiguring  = 0x02,
	RunlevelReady        = 0x03,
	RunlevelRunning      = 0x04,
	RunlevelRestarting   = 0x05,
	RunlevelHalting      = 0x06,
	RunlevelPanicing     = 0x07,
	RunlevelMAX          = 0x07
} Runlevel;


class Application {
	private:
		Runlevel      runlevel;
		time_t        time_offset;
	protected:
		ErrorContext  error_context;
		Configuration configuration;
		Environment   environment;
		Settings      settings;
		void          setTime(time_t time);
	public:
		Application();

		bool loadSettings();
		bool saveSettings();
		bool resetSettings();


		void                                  setRunlevel(Runlevel runlevel);
		Runlevel                              getRunlevel();
		const etl::string<GLOBAL_KEY_SIZE>&   getRunlevelName();

		bool                                  hasEnv(const etl::string<GLOBAL_KEY_SIZE>& key);
		const etl::string<GLOBAL_VALUE_SIZE>& getEnv(const etl::string<GLOBAL_KEY_SIZE>& key);
		void                                  setEnv(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value);
		void                                  delEnv(const etl::string<GLOBAL_KEY_SIZE>& key);

		bool                                  hasSetting(const etl::string<GLOBAL_KEY_SIZE>& key);
		const etl::string<GLOBAL_VALUE_SIZE>& getSetting(const etl::string<GLOBAL_KEY_SIZE>& key);
		void                                  setSetting(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value);
		void                                  delSetting(const etl::string<GLOBAL_KEY_SIZE>& key);

		void addErrorContext(const etl::string<GLOBAL_VALUE_SIZE>& context);
		void processError(const etl::string<GLOBAL_KEY_SIZE>& level, const etl::string<GLOBAL_KEY_SIZE>& id,
		                 const etl::string<GLOBAL_VALUE_SIZE>& message, const etl::string<GLOBAL_VALUE_SIZE>& details);

	static time_t getTime();

	static void addConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	       bool loadConfiguration();
	       bool applyConfiguration();

	static const etl::string<GLOBAL_VALUE_SIZE> Null;
	friend class EnvironmentWriter;
	friend void on_system_runlevel(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	friend void on_system_features(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	friend void on_system_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	friend void on_system_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
};


#endif

