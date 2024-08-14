#include <Adafruit_MCP23X17.h>
#include "globals.h"
#include "devices.h"


MCP23X17_Device* MCP23X17_Device::instances[APPLICATION_CONFIGURATION_MCP23X17_DEVICES] = { nullptr };


bool MCP23X17_Device::configure(const etl::string<GLOBAL_KEY_SIZE>& device_name) {
	bool  result = false;

	if(this->isConfigured()) {
		g_util_webserial.send("syslog/warn", "MCP23X17_Device::configure(): instance already configured");
		g_util_webserial.send("syslog/warn", this->device_type);
		g_util_webserial.send("syslog/warn", this->device_name);
		return false;
	}
	this->device_name = device_name;
	for(uint8_t i=0; i<APPLICATION_CONFIGURATION_MCP23X17_DEVICES; i++) {
		if(result == false && MCP23X17_Device::instances[i] == nullptr) {
			MCP23X17_Device::instances[i] = this;
			result = true;
		}
	}
	return result;
}


bool MCP23X17_Device::isInputDevice() {
	return false;
}


bool MCP23X17_Device::isOutputDevice() {
	return false;
}


MCP23X17_OutputDevice::MCP23X17_OutputDevice(const etl::string<GLOBAL_KEY_SIZE>& device_type)
                      :MCP23X17_Device(device_type) {
}


bool MCP23X17_OutputDevice::isOutputDevice() {
	return true;
}


bool MCP23X17_OutputDevice::configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& outputs) {
	bool  result = false;

	if(this->isConfigured()) {
		g_util_webserial.send("syslog/warn", "MCP23X17_OutputDevice::configure(): instance already configured");
		g_util_webserial.send("syslog/warn", this->device_type);
		g_util_webserial.send("syslog/warn", this->device_name);
		return false;
	}
	result = MCP23X17_Device::configure(device_name);
	for(uint8_t i=0; i<outputs.size(); i++) {
		JsonObject   output;
		const char*  pin = nullptr;
		const char*  value = nullptr;
		uint8_t      gpio;

		output = outputs[i].as<JsonObject>();
		if(output.containsKey("pin") == false || output.containsKey("label") == false || output.containsKey("value") == false) {
			g_util_webserial.send("syslog/error", "MCP23X17_OutputDevice::configure(): incomplete pin configuration");
			g_util_webserial.send("syslog/error", output);
			return false;
		}
		pin = output["pin"].as<const char*>();
		if(pin == nullptr || (pin[0] != 'A' && pin[0] != 'B') || pin[1] < 0x30 || pin[1] > 0x39) {
			g_util_webserial.send("syslog/error", "MCP23X17_OutputDevice::configure(): invalid pin in outputs (A0-A7,B0-B7)");
			g_util_webserial.send("syslog/error", pin);
			return false;
		}
		value = output["value"].as<const char*>();
		if(value == nullptr || (value[0] != 'h' && value[0] != 'l')) {
			g_util_webserial.send("syslog/error", "MCP23X17_OutputDevice::configure(): invalid value in output (low, high)");
			g_util_webserial.send("syslog/error", value);
			return false;
		}
		gpio = (pin[0]-'A')*8 + pin[1]-'0';
		this->pin_names[i] = MCP23X17::PIN_NAMES[gpio];
		if(value[0] == 'h') {
			this->pin_states[i] = PIN_HIGH;
		} else {
			this->pin_states[i] = PIN_LOW;
		}
		mcp23X17->pinMode(gpio, OUTPUT);
		mcp23X17->digitalWrite(gpio, this->pin_states[i]);
	}
	return result;
}


MCP23X17_InputDevice::MCP23X17_InputDevice(const etl::string<GLOBAL_KEY_SIZE>& device_type)
                     :MCP23X17_Device(device_type) {
}

 
bool MCP23X17_InputDevice::isInputDevice() {
	return true;
}


bool MCP23X17_InputDevice::configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events) {
	bool  result = false;

	if(this->isConfigured()) {
		g_util_webserial.send("syslog/warn", "MCP23X17_InputDevice::configure(): instance already configured");
		g_util_webserial.send("syslog/warn", this->device_type);
		g_util_webserial.send("syslog/warn", this->device_name);
		return false;
	}
	this->device_name = device_name;
	for(uint8_t i=0; i<APPLICATION_CONFIGURATION_MCP23X17_DEVICES; i++) {
		if(result == false && MCP23X17_Device::instances[i] == nullptr) {
			MCP23X17_Device::instances[i] = this;
			result = true;
		}
	}
	return result;
}


void MCP23X17_InputDevice::process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result) {
	result.createNestedObject("source");
	result["source"]["type"] = this->device_type.c_str();
	result["source"]["name"] = this->device_name.c_str();
	result.createNestedObject("device");
	if(pin_name.size() > 0 && pin_value.size() > 0) {
		result["device"]["pin"] = pin_name.c_str();
		result["device"]["value"] = pin_value.c_str();
	}
	result.createNestedObject("event");
}


// Rotary decoder ripped from https://github.com/brianlow/Rotary/

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
  {R_START,    R_CW_BEGIN,  R_CCW_BEGIN, R_START},
  {R_CW_NEXT,  R_START,     R_CW_FINAL,  R_START | DIR_CW},
  {R_CW_NEXT,  R_CW_BEGIN,  R_START,     R_START},
  {R_CW_NEXT,  R_CW_BEGIN,  R_CW_FINAL,  R_START},
  {R_CCW_NEXT, R_START,     R_CCW_BEGIN, R_START},
  {R_CCW_NEXT, R_CCW_FINAL, R_START,     R_START | DIR_CCW},
  {R_CCW_NEXT, R_CCW_FINAL, R_CCW_BEGIN, R_START},
};


bool MCP23X17_Rotary::configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events) {
	this->rotary_state = R_START;
	if(MCP23X17_InputDevice::configure(device_name, mcp23X17, inputs, events) == false) {
		g_util_webserial.send("syslog/error", "MCP23X17_Rotary::configure() failed");
		return false;
	}
	if(inputs.size() < 2) {
		g_util_webserial.send("syslog/error", "MCP23X17_Rotary::configure() => inputs not a list (or empty/missing/incomplete)");
		return false;
	}
	if(inputs.size() > 2) {
		g_util_webserial.send("syslog/warn", "MCP23X17_Rotary::configure() => inputs contains more than two entries, using only first two");
	}
	for(uint8_t i=0; i<2; i++) {
		JsonObject   input;
		const char*  pin = nullptr;
		uint8_t      gpio;

		input = inputs[i].as<JsonObject>();
		if(input.containsKey("pin") == false || input.containsKey("label") == false) {
			g_util_webserial.send("syslog/error", "MCP23X17_Rotary::configure(): incomplete pin configuration");
			g_util_webserial.send("syslog/error", input);
			return false;
		}
		pin = input["pin"].as<const char*>();
		if(pin == nullptr || (pin[0] != 'A' && pin[0] != 'B') || pin[1] < 0x30 || pin[1] > 0x39) {
			g_util_webserial.send("syslog/error", "MCP23X17_Rotary::configure(): invalid pin in inputs (A0-A7,B0-B7)");
			g_util_webserial.send("syslog/error", pin);
			return false;
		}
		gpio = (pin[0]-'A')*8 + pin[1]-'0';
		this->pin_names[i] = MCP23X17::PIN_NAMES[gpio];
		this->pin_states[i] = PIN_HIGH;
		mcp23X17->pinMode(gpio, INPUT_PULLUP);
	}
	return true;
}


void MCP23X17_Rotary::process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result) {
	for(uint8_t i=0; i<2; i++) {
		if(this->pin_names[i].compare(pin_name) == 0) {
			if(pin_value.compare(MCP23X17::PIN_VALUES[0]) == 0) {
				this->pin_states[i] = PIN_LOW;
			}
			if(pin_value.compare(MCP23X17::PIN_VALUES[1]) == 0) {
				this->pin_states[i] = PIN_HIGH;
			}
		}
	}
	this->rotary_state = ttable[this->rotary_state & 0x0f][((this->pin_states[1]) << 1) | ((this->pin_states[0]) << 0)];
	if(this->rotary_state & DIR_MASK) {
		MCP23X17_InputDevice::process(pin_name, pin_value, result);
		if((this->rotary_state & DIR_MASK) == DIR_CW) {
			result["event"]["delta"] = "+1";
		} else {
			result["event"]["delta"] = "-1";
		}
	}
}


bool MCP23X17_Switch::configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events) {
	bool result = false;

	result = MCP23X17_InputDevice::configure(device_name, mcp23X17, inputs, events);
	if(inputs.size() == 0) {
		g_util_webserial.send("syslog/error", "MCP23X17_Switch::configure() => inputs not a list (or empty/missing)");
		return false;
	}
	if(inputs.size() > 1) {
		g_util_webserial.send("syslog/warn", "MCP23X17_Switch::configure() => inputs contains more than one entry, using only first one");
	}
	if(result) {
		const char*  pin;
		uint8_t      gpio;
		bool         gpio_pullup = true;

		pin = nullptr;
		if(inputs[0].containsKey("pin") == false || inputs[0].containsKey("label") == false) {
			g_util_webserial.send("syslog/error", "MCP23X17_Switch::configure(): incomplete pin configuration");
			g_util_webserial.send("syslog/error", inputs[0].as<JsonVariant>());
			return false;
		}
		pin = inputs[0]["pin"].as<const char*>();
		if(pin == nullptr || (pin[0] != 'A' && pin[0] != 'B') || pin[1] < 0x30 || pin[1] > 0x39) {
			g_util_webserial.send("syslog/error", "MCP23X17_Switch::configure(): invalid pin in inputs (A0-A7,B0-B7)");
			g_util_webserial.send("syslog/error", pin);
			return false;
		}
		if(inputs[0].containsKey("pullup")) {
			gpio_pullup = inputs[0]["pullup"].as<bool>();
		}
		gpio = (pin[0]-'A')*8 + pin[1]-'0';
		this->pin_name = MCP23X17::PIN_NAMES[gpio];
		if(events.containsKey("high")) {
			this->event_high = events["high"].as<const char*>();
		}
		if(events.containsKey("low")) {
			this->event_low = events["low"].as<const char*>();
		}
		mcp23X17->pinMode(gpio, gpio_pullup ? INPUT_PULLUP : INPUT);
	}
	return result;
}


void MCP23X17_Switch::process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result) {
	if(this->pin_name.compare(pin_name) == 0) {
		MCP23X17_InputDevice::process(pin_name, pin_value, result);
		if(pin_value.compare(MCP23X17_PIN_VALUE_LOW) == 0) {
			result["event"]["status"] = this->event_low.c_str();
		}
		if(pin_value.compare(MCP23X17_PIN_VALUE_HIGH) == 0) {
			result["event"]["status"] = this->event_high.c_str();
		}
	}
}


bool MCP23X17_Button::configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events) {
	return MCP23X17_Switch::configure(device_name, mcp23X17, inputs, events);
}


void MCP23X17_Button::process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result) {
	if(pin_name.compare(this->pin_name) == 0) {
		if(pin_value.compare(MCP23X17::PIN_VALUES[1]) == 0) {
			MCP23X17_InputDevice::process(pin_name, pin_value, result);
			result["event"]["status"] = "clicked";
		}
	}
};

