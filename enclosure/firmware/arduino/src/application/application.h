#ifndef __APPLICATION_APPLICATION_H__
#define __APPLICATION_APPLICATION_H__

#include <etl/string.h>
#include <etl/map.h>
#include <etl/list.h>
#include <ArduinoJson.h>

#include "application/settings.h"
#include "application/environment.h"

typedef etl::list<etl::string<GLOBAL_VALUE_SIZE>, APPLICATION_ERROR_MAX> ErrorContext;

typedef enum {
	StatusUnknown      = 0x00,
	StatusStarting     = 0x01,
	StatusConfiguring  = 0x02,
	StatusReady        = 0x03,
	StatusRunning      = 0x04,
	StatusRebooting    = 0x05,
	StatusHalting      = 0x06,
	StatusPanicing     = 0x07,
	StatusMAX          = 0x07
} Status;


class Application {
	private:
		Status        status;
		time_t        time_offset;
	protected:
		ErrorContext  error_context;
		Environment   environment;
		Settings      settings;
		void          setTime(time_t time);
	public:
		Application();

		bool loadSettings();
		bool saveSettings();
		bool resetSettings();

		void                                  setStatus(Status status) { if(status > this->status && status <= StatusMAX) { this->status = status; } };
		Status                                getStatus() { return this->status; };
		const etl::string<GLOBAL_KEY_SIZE>&   getStatusName();

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

	static void onConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);

	static const etl::string<GLOBAL_VALUE_SIZE> Null;
	friend class EnvironmentWriter;
	friend void on_application_runtime(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	friend void on_application_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	friend void on_application_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
};


#endif

