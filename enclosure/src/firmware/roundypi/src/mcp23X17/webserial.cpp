#include "globals.h"
#include "webserial.h"
#include "mcp23X17.h"


void on_mcp23X17_setup(JSONVar parameter) {
	if(parameter.hasOwnProperty("mcp23X17")) {
		uint8_t i2c_addr = 0x20;
		uint8_t pin_sda = 0;
		uint8_t pin_scl = 1;

		if(parameter.hasOwnProperty("i2c-address")) {
			i2c_addr = (int)parameter["i2c-address"];
		}
		if(parameter.hasOwnProperty("pin-sda")) {
			pin_sda = (int)parameter["pin-sda"];
		}
		if(parameter.hasOwnProperty("pin-scl")) {
			pin_scl = (int)parameter["pin-scl"];
		}
		g_mcp23X17.config_i2c(i2c_addr, pin_sda, pin_scl);
		return;
	}
	if(parameter.hasOwnProperty("device")) {
		const char*  device_name = NULL;
		const char*  device_type = NULL;

		device_name = parameter["device"]["name"];
		device_type = parameter["device"]["type"];
		if(parameter["device"].hasOwnProperty("inputs")) {
			static JSONVar  device_inputs;
			static JSONVar  device_actions;

			device_inputs = parameter["device"]["inputs"];
			device_actions = parameter["device"]["actions"];
			g_mcp23X17.config_inputs(device_name, device_type, device_inputs, device_actions);
		}
//TODO		if(parameter.hasOwnProperty("outputs")) {
//TODO			JSONVar device_outputs;
//TODO
//TODO			device_outputs = parameter["device"]["outputs"];
//TODO			g_mcp23X17.config_outputs(device_name, device_type, device_outputs);
//TODO		}
	}
}


void on_mcp23X17_loop(JSONVar parameter) {
	g_mcp23X17.start();
}

