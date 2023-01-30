#include <ArduinoJson.h>

void on_application_runtime(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
void on_application_environment(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
void on_application_settings(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);

