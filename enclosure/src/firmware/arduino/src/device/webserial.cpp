#include <ArduinoJson.h>

#include "globals.h"
#include "device/sdcard/sdcard.h"
#include "device/mcp23X17/mcp23X17.h"


void on_device_display(const JsonVariant& data) {
	if(data.containsKey("backlight")) {
		bool  backlight = true;

		if(strncmp(data["backlight"].as<const char*>(), "off", 4) == 0) {
			backlight = false;
		}
		digitalWrite(TFT_BL, backlight ? HIGH : LOW);
	}
}


void on_device_sdcard(const JsonVariant& data) {
//TODO: implement logic
}


void on_device_mcp23X17(const JsonVariant& data) {
	if(data.containsKey("init")) {
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
		if(data["init"].containsKey("i2c-address")) {
			i2c_address = data["init"]["i2c-address"].as<int>();
		}
		if(data["init"].containsKey("i2c-pin-sda")) {
			i2c_pin_sda = data["init"]["pin-sda"].as<int>();
		}
		if(data["init"].containsKey("i2c-pin-scl")) {
			i2c_pin_scl = data["init"]["pin-scl"].as<int>();
		}
		g_device_mcp23X17.init(i2c_address, i2c_pin_sda, i2c_pin_scl);
	}
	if(data.containsKey("config")) {
		const char*  device_type = nullptr;
		const char*  device_name = nullptr;

		device_type = data["config"]["device"]["type"].as<const char*>();
		device_name = data["config"]["device"]["name"].as<const char*>();
		if(data["config"]["device"].containsKey("inputs")) {
			JsonArray   device_inputs;
			JsonObject  device_actions;

			device_inputs = data["config"]["device"]["inputs"].as<JsonArray>();
			device_actions = data["config"]["device"]["actions"].as<JsonObject>();
			g_device_mcp23X17.config_inputs(device_type, device_name, device_inputs, device_actions);
		}
		if(data["config"]["device"].containsKey("outputs")) {
			JsonArray device_outputs;

			device_outputs = data["config"]["device"]["outputs"].as<JsonArray>();
			g_device_mcp23X17.config_outputs(device_type, device_name, device_outputs);
		}
	}
	if(data.containsKey("start")) {
		if(data["start"].as<bool>() == true) {
			g_device_mcp23X17.start();
		}
	}
}

