#include "globals.h"
#include "webserial.h"
#include "mcp23017.h"
#include <Adafruit_MCP23X17.h>


void on_mcp23017_begin(JSONVar parameter) {
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
	mcp23017_begin(i2c_addr, pin_sda, pin_scl);
}


void on_mcp23017_config(JSONVar parameter) {
	if(parameter.hasOwnProperty("inputs")) {
		JSONVar  inputs_keys;
		uint32_t inputs_length;

		inputs_keys = parameter["inputs"].keys();
		inputs_length = inputs_keys.length();
		for(uint32_t i=0; i<inputs_length; i++) {
			const char* name = NULL;
			const char* value = NULL;

			name = inputs_keys[i];
			value = parameter["inputs"][name];
			mcp23017_config_inputs(name, value);
		}
	}
	if(parameter.hasOwnProperty("outputs")) {
	}
	if(parameter.hasOwnProperty("interrupts")) {
	}
	//TODO
}

