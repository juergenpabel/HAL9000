#include <ArduinoJson.h>

#include "globals.h"
#include "device/sdcard/sdcard.h"
#include "device/mcp23X17/mcp23X17.h"


void on_device_display(const JsonVariant& parameter) {
	if(parameter.containsKey("backlight")) {
		bool  backlight = true;

		if(parameter["backlight"].as<std::string>().compare("off") == 0) {
			backlight = false;
		}
		digitalWrite(TFT_BL, backlight ? HIGH : LOW);
	}
}


void on_device_sdcard(const JsonVariant& parameter) {
//TODO: implement logic
}


void on_device_mcp23X17(const JsonVariant& parameter) {
	if(parameter.containsKey("init")) {
		uint8_t i2c_address = SYSTEM_SETTINGS_MCP23X17_ADDRESS;
		uint8_t i2c_pin_sda = SYSTEM_SETTINGS_MCP23X17_PIN_SDA;
		uint8_t i2c_pin_scl = SYSTEM_SETTINGS_MCP23X17_PIN_SCL;

		if(g_system_settings.count("device/mcp23X17:i2c/address") == 1) {
			i2c_address = atoi(g_system_settings["device/mcp23X17:i2c/address"].c_str());
		}
		if(g_system_settings.count("device/mcp23X17:i2c/pin-sda") == 1) {
			i2c_pin_sda = atoi(g_system_settings["device/mcp23X17:i2c/pin-sda"].c_str());
		}
		if(g_system_settings.count("device/mcp23X17:i2c/pin-scl") == 1) {
			i2c_pin_scl = atoi(g_system_settings["device/mcp23X17:i2c/pin-scl"].c_str());
		}
		if(parameter["init"].containsKey("i2c-address")) {
			i2c_address = parameter["init"]["i2c-address"].as<int>();
		}
		if(parameter["init"].containsKey("i2c-pin-sda")) {
			i2c_pin_sda = parameter["init"]["pin-sda"].as<int>();
		}
		if(parameter["init"].containsKey("i2c-pin-scl")) {
			i2c_pin_scl = parameter["init"]["pin-scl"].as<int>();
		}
		g_device_mcp23X17.init(i2c_address, i2c_pin_sda, i2c_pin_scl);
	}
	if(parameter.containsKey("config")) {
		const char*  device_type = NULL;
		const char*  device_name = NULL;

		device_type = parameter["config"]["device"]["type"].as<const char*>();
		device_name = parameter["config"]["device"]["name"].as<const char*>();
		if(parameter["config"]["device"].containsKey("inputs")) {
			JsonArray   device_inputs;
			JsonObject  device_actions;

			device_inputs = parameter["config"]["device"]["inputs"].as<JsonArray>();
			device_actions = parameter["config"]["device"]["actions"].as<JsonObject>();
			g_device_mcp23X17.config_inputs(device_type, device_name, device_inputs, device_actions);
		}
//TODO		if(parameter["config"]["device"].containsKey("outputs")) {
//TODO			JsonVariant device_outputs;
//TODO
//TODO			device_outputs = parameter["config"]["device"]["outputs"].as<JsonVariant>();
//TODO			g_device_mcp23X17.config_outputs(device_name, device_type, device_outputs);
//TODO		}
	}
	if(parameter.containsKey("start")) {
		if(parameter["start"].as<bool>() == true) {
			g_device_mcp23X17.start();
		}
	}
}

