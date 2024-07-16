#ifndef __APPLICATION_APPLICATION_H__
#define __APPLICATION_APPLICATION_H__

#include <etl/string.h>
#include <etl/map.h>
#include <ArduinoJson.h>

#include "application/error.h"
#include "application/settings.h"
#include "application/environment.h"

typedef enum {
	StatusUnknown      = 0x00,
	StatusStarting     = 0x01,
	StatusConfiguring  = 0x02,
	StatusWaiting      = 0x03,
	StatusReady        = 0x04,
	StatusRunning      = 0x05,
	StatusResetting    = 0x06,
	StatusRebooting    = 0x07,
	StatusHalting      = 0x08,
	StatusPanicing     = 0x09,
	StatusMAX          = 0x09
} Status;


class Application {
	private:
		Status      m_status;
	protected:
		Environment m_environment;
		Settings    m_settings;
		ErrorQueue  m_errors;
	public:
		Application();
		bool loadSettings();
		bool saveSettings();
		bool resetSettings();

		void                                  setStatus(Status status) { if(status > this->m_status && status <= StatusMAX) { this->m_status = status; } };
		Status                                getStatus() { return this->m_status; };
		const etl::string<GLOBAL_KEY_SIZE>&   getStatusName();

		bool                                  hasEnv(const etl::string<GLOBAL_KEY_SIZE>& key);
		const etl::string<GLOBAL_VALUE_SIZE>& getEnv(const etl::string<GLOBAL_KEY_SIZE>& key);
		void                                  setEnv(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value);
		void                                  delEnv(const etl::string<GLOBAL_KEY_SIZE>& key);

		bool                                  hasSetting(const etl::string<GLOBAL_KEY_SIZE>& key);
		const etl::string<GLOBAL_VALUE_SIZE>& getSetting(const etl::string<GLOBAL_KEY_SIZE>& key);
		void                                  setSetting(const etl::string<GLOBAL_KEY_SIZE>& key, const etl::string<GLOBAL_VALUE_SIZE>& value);
		void                                  delSetting(const etl::string<GLOBAL_KEY_SIZE>& key);

		void notifyError(const etl::string<GLOBAL_KEY_SIZE>& level, const etl::string<GLOBAL_KEY_SIZE>& id,
		                 const etl::string<GLOBAL_VALUE_SIZE>& message, const etl::string<GLOBAL_KEY_SIZE>& detail);

	static void onConfiguration(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	       void onWaiting();
	       void onReady();
	       void onRunning();

	static const etl::string<GLOBAL_VALUE_SIZE> Null;
	friend class EnvironmentWriter;
	friend void on_application_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
	friend void on_application_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
};


#endif

