#include <etl/string.h>
#include <ArduinoJson.h>

void on_system_runlevel(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
void on_system_features(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
void on_system_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
void on_system_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);

