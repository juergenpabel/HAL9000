#ifndef __ROUNDYPI_MCP23X17_DEVICES_H__
#define __ROUNDYPI_MCP23X17_DEVICES_H__

#include <Adafruit_MCP23X17.h>
#include "globals.h"


class MCP23X17_Device {
	public:
		static MCP23X17_Device* instances[SYSTEM_SETTINGS_MCP23X17_DEV_INSTANCES];
		const uint8_t PIN_LOW  = 0x00;
		const uint8_t PIN_HIGH = 0x01;
	protected:
		const char* type = NULL;
		char        name[GLOBAL_KEY_SIZE] = {0};
	public:
		MCP23X17_Device(const char* type);
		virtual bool isConfigured() { return this->name[0] != '\0'; };
		virtual bool configure(const char* name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& actions);
		const char* getName() { return this->name; };
		virtual void process(const char* pin, const char* pin_value, JsonDocument& result);
};


class MCP23X17_Rotary : public MCP23X17_Device {
	protected:
		const char* pins[2] = { NULL , NULL };
		uint8_t     pins_state[2] = { PIN_HIGH, PIN_HIGH };
		uint8_t     rotary_state = 0x00;
	public:
		MCP23X17_Rotary() : MCP23X17_Device("rotary") {};
		virtual bool configure(const char* name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& actions);
		virtual void process(const char* pin, const char* pin_value, JsonDocument& result);
};


class MCP23X17_Switch : public MCP23X17_Device {
	protected:
		const char* pin = NULL;
	public:
		MCP23X17_Switch(const char* type = "switch") : MCP23X17_Device(type) {};
		virtual bool configure(const char* name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& actions);
		virtual void process(const char* pin, const char* pin_value, JsonDocument& result);
};


class MCP23X17_Button : public MCP23X17_Switch {
	protected:
	public:
		MCP23X17_Button() : MCP23X17_Switch("button") {};
		virtual bool configure(const char* name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& actions);
		virtual void process(const char* pin, const char* pin_value, JsonDocument& result);
};


class MCP23X17_Toggle : public MCP23X17_Switch {
	protected:
		bool state = false;
		char action_true[GLOBAL_KEY_SIZE] = {0};
		char action_false[GLOBAL_KEY_SIZE] = {0};
	public:
		MCP23X17_Toggle() : MCP23X17_Switch("toggle") {};
		virtual bool configure(const char* name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& actions);
		virtual void process(const char* pin, const char* pin_value, JsonDocument& result);
};


#endif

