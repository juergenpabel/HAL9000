#include "globals.h"
#include "webserial.h"
#include "mcp23017.h"
#include <Adafruit_MCP23X17.h>


void on_mcp23017_setup(JSONVar parameter) {
	if(parameter.hasOwnProperty("mcp23017")) {
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
		mcp23017_config_i2c(i2c_addr, pin_sda, pin_scl);
	}
	if(parameter.hasOwnProperty("inputs")) {
		JSONVar  inputs_keys;
		uint32_t inputs_length;

		inputs_keys = parameter["inputs"].keys();
		inputs_length = inputs_keys.length();
		for(uint32_t i=0; i<inputs_length; i++) {
			const char* event_name = NULL;
			const char* pin_name = NULL;
			const char* trigger_state = NULL;

			event_name = inputs_keys[i];
			pin_name = parameter["inputs"][event_name]["pin"];
			if(parameter["inputs"][event_name].hasOwnProperty("trigger")) {
				trigger_state = parameter["inputs"][event_name]["trigger"];
			}
			mcp23017_config_inputs(event_name, pin_name, trigger_state);
		}
	}
	if(parameter.hasOwnProperty("outputs")) {
	}
	if(parameter.hasOwnProperty("interrupts")) {
	}
	//TODO
}


void on_mcp23017_loop(JSONVar parameter) {
	uint8_t  core_nr = 2;
	
	if(parameter.hasOwnProperty("core")) {
		core_nr = (int)parameter["core"];
	}
	mcp23017_set_core(core_nr);
}

