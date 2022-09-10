#include <string>
#include <JSONVar.h>

#include "globals.h"
#include "device/sdcard/sdcard.h"
#include "device/mcp23X17/mcp23X17.h"


void on_device_display(JSONVar parameter) {
	if(parameter.hasOwnProperty("backlight")) {
		bool  backlight = true;

		if(arduino::String("off") == parameter["backlight"]) {
			backlight = false;
		}
		digitalWrite(TFT_BL, backlight ? HIGH : LOW);
	}
}


void on_device_sdcard(JSONVar parameter) {
//TODO: implement logic
}


void on_device_mcp23X17(JSONVar parameter) {
	if(parameter.hasOwnProperty("init")) {
		uint8_t i2c_address = SYSTEM_SETTINGS_MCP23X17_ADDRESS;
		uint8_t i2c_pin_sda = SYSTEM_SETTINGS_MCP23X17_PIN_SDA;
		uint8_t i2c_pin_scl = SYSTEM_SETTINGS_MCP23X17_PIN_SCL;

		if(g_system_settings.count("device/mcp23X17:i2c/address") == 1) {
			i2c_address = std::stoi(g_system_settings["device/mcp23X17:i2c/address"]);
		}
		if(g_system_settings.count("device/mcp23X17:i2c/pin-sda") == 1) {
			i2c_pin_sda = std::stoi(g_system_settings["device/mcp23X17:i2c/pin-sda"]);
		}
		if(g_system_settings.count("device/mcp23X17:i2c/pin-scl") == 1) {
			i2c_pin_scl = std::stoi(g_system_settings["device/mcp23X17:i2c/pin-scl"]);
		}
		if(parameter["init"].hasOwnProperty("i2c-address")) {
			i2c_address = (int)parameter["init"]["i2c-address"];
		}
		if(parameter["init"].hasOwnProperty("i2c-pin-sda")) {
			i2c_pin_sda = (int)parameter["init"]["pin-sda"];
		}
		if(parameter["init"].hasOwnProperty("i2c-pin-scl")) {
			i2c_pin_scl = (int)parameter["init"]["pin-scl"];
		}
		g_device_mcp23X17.init(i2c_address, i2c_pin_sda, i2c_pin_scl);
	}
	if(parameter.hasOwnProperty("config")) {
		const char*  device_type = NULL;
		const char*  device_name = NULL;

		device_type = parameter["config"]["device"]["type"];
		device_name = parameter["config"]["device"]["name"];
		if(parameter["config"]["device"].hasOwnProperty("inputs")) {
			static JSONVar  device_inputs;
			static JSONVar  device_actions;

			device_inputs = parameter["config"]["device"]["inputs"];
			device_actions = parameter["config"]["device"]["actions"];
			g_device_mcp23X17.config_inputs(device_type, device_name, device_inputs, device_actions);
		}
//TODO		if(parameter["config"]["device"].hasOwnProperty("outputs")) {
//TODO			JSONVar device_outputs;
//TODO
//TODO			device_outputs = parameter["config"]["device"]["outputs"];
//TODO			g_device_mcp23X17.config_outputs(device_name, device_type, device_outputs);
//TODO		}
	}
	if(parameter.hasOwnProperty("start")) {
		if(true == (bool)parameter["start"]) {
			g_device_mcp23X17.start();
		}
	}
}

