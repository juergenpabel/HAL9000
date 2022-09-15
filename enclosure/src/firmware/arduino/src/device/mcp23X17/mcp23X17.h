#ifndef __ROUNDYPI_MCP23X17_H__
#define __ROUNDYPI_MCP23X17_H__

#include <Adafruit_MCP23X17.h>
#include <ArduinoJson.h>
#include <etl/string.h>

#include "globals.h"


class MCP23X17 {
	friend class MCP23X17_Rotary;
	friend class MCP23X17_Switch;
	friend class MCP23X17_Button;
	friend class MCP23X17_Toggle;
	friend class MCP23X17_DigitalOut;
	protected:
		static etl::string<2> PIN_NAMES[16];
		static etl::string<4> PIN_VALUES[2];
	private:
		uint8_t            status;
		TwoWire            wire;
		Adafruit_MCP23X17  mcp23X17;
		uint16_t           mcp23X17_gpio_values;
	public:
		MCP23X17();
		void init();
		void init(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl);
		void config_inputs(const etl::string<GLOBAL_VALUE_SIZE>& device_type, const etl::string<GLOBAL_VALUE_SIZE>& device_name, const JsonArray& inputs, const JsonObject& actions);
		void config_outputs(const etl::string<GLOBAL_VALUE_SIZE>& device_type, const etl::string<GLOBAL_VALUE_SIZE>& device_name, const JsonArray& outputs);

		void start();
		void check();
	protected:
		static void loop();
};

#endif

