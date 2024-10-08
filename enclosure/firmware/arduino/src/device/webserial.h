#include <etl/string.h>
#include <ArduinoJson.h>

void on_device_board(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
void on_device_display(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);
void on_device_microcontroller(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data);

