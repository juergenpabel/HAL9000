#include <Adafruit_MCP23X17.h>
#include "globals.h"
#include "devices.h"


MCP23X17_Device* MCP23X17_Device::instances[MCP23X17_INSTANCES] = { NULL };


MCP23X17_Device::MCP23X17_Device(const char* type) {
	this->type = type;
}

 
bool MCP23X17_Device::configure(const char* name, Adafruit_MCP23X17* mcp23X17, JSONVar& inputs, JSONVar& actions) {
	bool  result = false;

	if(this->name[0] != '\0') {
		g_webserial.warn("MCP23X17_Device::configure(): instance already configured");
		g_webserial.warn(this->type);
		g_webserial.warn(this->name);
		return false;
	}
	strncpy(this->name, name, MaximumKeyNameLength-1);
	for(uint8_t i=0; i<MCP23X17_INSTANCES; i++) {
		if(result == false && MCP23X17_Device::instances[i] == NULL) {
			MCP23X17_Device::instances[i] = this;
			result = true;
		}
	}
	return result;
}


#define R_START     0x00
#define R_CW_FINAL  0x01
#define R_CW_BEGIN  0x02
#define R_CW_NEXT   0x03
#define R_CCW_BEGIN 0x04
#define R_CCW_FINAL 0x05
#define R_CCW_NEXT  0x06

#define DIR_NONE    0x00
#define DIR_CW      0x10
#define DIR_CCW     0x20
#define DIR_MASK    0x30

static const unsigned char ttable[7][4] = {
  // R_START
  {R_START,    R_CW_BEGIN,  R_CCW_BEGIN, R_START},
  // R_CW_FINAL
  {R_CW_NEXT,  R_START,     R_CW_FINAL,  R_START | DIR_CW},
  // R_CW_BEGIN
  {R_CW_NEXT,  R_CW_BEGIN,  R_START,     R_START},
  // R_CW_NEXT
  {R_CW_NEXT,  R_CW_BEGIN,  R_CW_FINAL,  R_START},
  // R_CCW_BEGIN
  {R_CCW_NEXT, R_START,     R_CCW_BEGIN, R_START},
  // R_CCW_FINAL
  {R_CCW_NEXT, R_CCW_FINAL, R_START,     R_START | DIR_CCW},
  // R_CCW_NEXT
  {R_CCW_NEXT, R_CCW_FINAL, R_CCW_BEGIN, R_START},
};


bool MCP23X17_Rotary::configure(const char* name, Adafruit_MCP23X17* mcp23X17, JSONVar& inputs, JSONVar& actions) {
	bool result = false;

	this->rotary_state = R_START;
	result = MCP23X17_Device::configure(name, mcp23X17, inputs, actions);
	if(result == false) {
		g_webserial.warn("MCP23X17_Device::configure() failed");
		return false;
	}
	if(inputs.length() < 2) {
		g_webserial.warn("MCP23X17_Switch::configure() => inputs not a list (or empty/missing/incomplete)");
		return false;
	}
	if(inputs.length() > 2) {
		g_webserial.warn("MCP23X17_Switch::configure() => inputs contains more than two entries, using only first two");
	}
	for(uint8_t i=0; i<2; i++) {
		const char*  pin;
		uint8_t      gpio;

		pin = NULL;
		if(inputs[i].hasOwnProperty("pin") == false || inputs[i].hasOwnProperty("label") == false) {
			g_webserial.warn("MCP23X17_Device::configure(): incomplete pin configuration");
			g_webserial.warn(inputs[i]);
			return false;
		}
		pin = inputs[i]["pin"];
		if(pin == NULL || (pin[0] != 'A' && pin[0] != 'B') || pin[1] < 0x30 || pin[1] > 0x39) {
			g_webserial.warn("MCP23X17_Device::configure(): invalid pin in inputs (A0-A7,B0-B7)");
			g_webserial.warn(pin);
			return false;
		}
		gpio = (pin[0]-'A')*8 + pin[1]-'0';
		this->pins[i] = MCP23X17::PIN_NAMES[gpio];
		this->pins_state[i] = PIN_HIGH;
		mcp23X17->pinMode(gpio, INPUT_PULLUP);
//TODO:		mcp23X17->setupInterruptPin(gpio, LOW);
	}
	return result;
}


JSONVar MCP23X17_Rotary::process(const char* pin, const char* pin_value) {
	JSONVar result;

	for(uint8_t i=0; i<2; i++) {
		if(this->pins[i] == pin || strncmp(this->pins[i], pin, MaximumKeyNameLength) == 0) {
			if(pin_value == MCP23X17::PIN_VALUES[0] || strncmp(pin_value, MCP23X17::PIN_VALUES[0], MaximumKeyNameLength) == 0) {
				this->pins_state[i] = PIN_LOW;
			}
			if(pin_value == MCP23X17::PIN_VALUES[1] || strncmp(pin_value, MCP23X17::PIN_VALUES[1], MaximumKeyNameLength) == 0) {
				this->pins_state[i] = PIN_HIGH;
			}
		}
	}
	this->rotary_state = ttable[this->rotary_state & 0x0f][((this->pins_state[1]) << 1) | ((this->pins_state[0]) << 0)];
	switch(this->rotary_state & DIR_MASK) {
		case DIR_NONE:
			break;
		case DIR_CW:
			result["delta"] = "+1";
			break;
		case DIR_CCW:
			result["delta"] = "-1";
			break;
		default:
			result["error:state"] = this->rotary_state;

	};
	return result;
}


bool MCP23X17_Switch::configure(const char* name, Adafruit_MCP23X17* mcp23X17, JSONVar& inputs, JSONVar& actions) {
	bool result = false;

	result = MCP23X17_Device::configure(name, mcp23X17, inputs, actions);
	if(inputs.length() == 0) {
		g_webserial.warn("MCP23X17_Switch::configure() => inputs not a list (or empty/missing)");
		return false;
	}
	if(inputs.length() > 1) {
		g_webserial.warn("MCP23X17_Switch::configure() => inputs contains more than one entry, using only first one");
	}
	if(result) {
		const char*  pin;
		uint8_t      gpio;
		bool         gpio_pullup = true;

		pin = NULL;
		if(inputs[0].hasOwnProperty("pin") == false || inputs[0].hasOwnProperty("label") == false) {
			g_webserial.warn("MCP23X17_Device::configure(): incomplete pin configuration");
			g_webserial.warn(inputs[0]);
			return false;
		}
		pin = inputs[0]["pin"];
		if(pin == NULL || (pin[0] != 'A' && pin[0] != 'B') || pin[1] < 0x30 || pin[1] > 0x39) {
			g_webserial.warn("MCP23X17_Device::configure(): invalid pin in inputs (A0-A7,B0-B7)");
			g_webserial.warn(pin);
			return false;
		}
		if(inputs[0].hasOwnProperty("pullup")) {
			gpio_pullup = inputs[0]["pullup"];
		}
		gpio = (pin[0]-'A')*8 + pin[1]-'0';
		this->pin = MCP23X17::PIN_NAMES[gpio];
		mcp23X17->pinMode(gpio, gpio_pullup ? INPUT_PULLUP : INPUT);
//TODO:		mcp23X17->setupInterruptPin(gpio, LOW);
	}
	return result;
}


JSONVar MCP23X17_Switch::process(const char* pin, const char* pin_value) {
	JSONVar result;

	if(this->pin == pin || strncmp(this->pin, pin, MaximumKeyNameLength) == 0) {
		result[pin] = pin_value;
	}
	return result;
}


bool MCP23X17_Button::configure(const char* name, Adafruit_MCP23X17* mcp23X17, JSONVar& inputs, JSONVar& actions) {
	bool result = false;

	result = MCP23X17_Switch::configure(name, mcp23X17, inputs, actions);
	return result;
}


JSONVar MCP23X17_Button::process(const char* pin, const char* pin_value) {
	JSONVar result;

	if(this->pin == pin || strncmp(this->pin, pin, MaximumKeyNameLength) == 0) {
		if(strncmp(pin_value, MCP23X17::PIN_VALUES[1], MaximumKeyNameLength) == 0) {
			result["status"] = "clicked";
		}
	}
	return result;
};


bool MCP23X17_Toggle::configure(const char* name, Adafruit_MCP23X17* mcp23X17, JSONVar& inputs, JSONVar& actions) {
	bool result = false;
	const char* pin = NULL;

	result = MCP23X17_Switch::configure(name, mcp23X17, inputs, actions);
	if(actions.hasOwnProperty("false")) {
		strncpy(this->action_false, actions["false"], MaximumKeyNameLength-1);
	}
	if(actions.hasOwnProperty("true")) {
		strncpy(this->action_true, actions["true"], MaximumKeyNameLength-1);
	}
	return result;
}


JSONVar MCP23X17_Toggle::process(const char* pin, const char* pin_value) {
	JSONVar result;

	if(this->pin == pin || strncmp(this->pin, pin, MaximumKeyNameLength) == 0) {
		if(strncmp(pin_value, MCP23X17::PIN_VALUES[1], MaximumKeyNameLength) == 0) {
			this->state = !this->state;
			result["status"] = this->state ? this->action_true : this->action_false;
		}
	}
	return result;
};

