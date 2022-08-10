#include <JSONVar.h>

#include "globals.h"
#include "device/sdcard/sdcard.h"
#include "device/mcp23X17/mcp23X17.h"


void on_device_display(JSONVar parameter) {
	if(parameter.hasOwnProperty("backlight")) {
		digitalWrite(TFT_BL, (bool)parameter["backlight"] ? HIGH : LOW);
	}
}

void on_device_sdcard(JSONVar parameter) {
	//TODO
}


void on_device_mcp23X17(JSONVar parameter) {
	if(parameter.hasOwnProperty("init")) {
		uint8_t i2c_addr = 0x20;
		uint8_t pin_sda = 0;
		uint8_t pin_scl = 1;

		//TODO:g_system_settings
		if(parameter["init"].hasOwnProperty("i2c-address")) {
			i2c_addr = (int)parameter["init"]["i2c-address"];
		}
		if(parameter["init"].hasOwnProperty("pin-sda")) {
			pin_sda = (int)parameter["init"]["pin-sda"];
		}
		if(parameter["init"].hasOwnProperty("pin-scl")) {
			pin_scl = (int)parameter["init"]["pin-scl"];
		}
		g_device_mcp23X17.init(i2c_addr, pin_sda, pin_scl);
	}
	if(parameter.hasOwnProperty("config")) {
		const char*  device_name = NULL;
		const char*  device_type = NULL;

		device_name = parameter["config"]["device"]["name"];
		device_type = parameter["config"]["device"]["type"];
		if(parameter["config"]["device"].hasOwnProperty("inputs")) {
			static JSONVar  device_inputs;
			static JSONVar  device_actions;

			device_inputs = parameter["config"]["device"]["inputs"];
			device_actions = parameter["config"]["device"]["actions"];
			g_device_mcp23X17.config_inputs(device_name, device_type, device_inputs, device_actions);
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

