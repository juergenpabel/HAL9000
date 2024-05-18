#ifndef __ROUNDYPI_MCP23X17_DEVICES_H__
#define __ROUNDYPI_MCP23X17_DEVICES_H__

#include <Adafruit_MCP23X17.h>
#include "globals.h"

#define APPLICATION_CONFIGURATION_MCP23X17_DEVICES 10


class MCP23X17_Device {
	friend class MCP23X17;
	public:
		const uint8_t PIN_LOW  = 0x00;
		const uint8_t PIN_HIGH = 0x01;
	protected:
		static MCP23X17_Device* instances[APPLICATION_CONFIGURATION_MCP23X17_DEVICES];
		etl::string<GLOBAL_KEY_SIZE> device_type;
		etl::string<GLOBAL_KEY_SIZE> device_name;
	public:
		MCP23X17_Device(const etl::string<GLOBAL_KEY_SIZE>& device_type) { this->device_type = device_type; };
		bool isConfigured() { return this->device_name.size() > 0; };
		const etl::string<GLOBAL_KEY_SIZE>& getName() { return this->device_name; };
		virtual bool isInputDevice();
		virtual bool isOutputDevice();
	protected:
		bool configure(const etl::string<GLOBAL_KEY_SIZE>& device_name);
};


class MCP23X17_OutputDevice : public MCP23X17_Device {
	protected:
		etl::string<2>  pin_names[8];
		uint8_t         pin_states[8];
	public:
		MCP23X17_OutputDevice(const etl::string<GLOBAL_KEY_SIZE>& type);
		bool configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& outputs);
		virtual bool isOutputDevice();
};


class MCP23X17_DigitalOut : public MCP23X17_OutputDevice {
	public:
		MCP23X17_DigitalOut() : MCP23X17_OutputDevice("digital") {};
};


class MCP23X17_InputDevice : public MCP23X17_Device {
	public:
		MCP23X17_InputDevice(const etl::string<GLOBAL_KEY_SIZE>& type);
		virtual bool configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events);
		virtual bool isInputDevice();
		virtual void process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result);
};


class MCP23X17_Rotary : public MCP23X17_InputDevice {
	protected:
		etl::string<2>  pin_names[2];
		uint8_t         pin_states[2] = { PIN_HIGH, PIN_HIGH };
		uint8_t         rotary_state = 0x00;
	public:
		MCP23X17_Rotary() : MCP23X17_InputDevice("rotary") {};
		virtual bool configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events);
		virtual void process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result);
};


class MCP23X17_Switch : public MCP23X17_InputDevice {
	protected:
		etl::string<2>  pin_name;
		etl::string<GLOBAL_KEY_SIZE> event_low;
		etl::string<GLOBAL_KEY_SIZE> event_high;
	public:
		MCP23X17_Switch(const etl::string<GLOBAL_KEY_SIZE>& device_type = "switch") : MCP23X17_InputDevice(device_type) {};
		virtual bool configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events);
		virtual void process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result);
};


class MCP23X17_Button : public MCP23X17_Switch {
	public:
		MCP23X17_Button() : MCP23X17_Switch("button") {};
		virtual bool configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events);
		virtual void process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result);
};


class MCP23X17_Toggle : public MCP23X17_Switch {
	protected:
		bool state = false;
	public:
		MCP23X17_Toggle() : MCP23X17_Switch("toggle") {};
		virtual bool configure(const etl::string<GLOBAL_KEY_SIZE>& device_name, Adafruit_MCP23X17* mcp23X17, const JsonArray& inputs, const JsonObject& events);
		virtual void process(const etl::string<2>& pin_name, const etl::string<4>& pin_value, JsonDocument& result);
};


#endif

