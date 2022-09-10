#ifndef __ROUNDYPI_MCP23X17_H__
#define __ROUNDYPI_MCP23X17_H__

#include <Adafruit_MCP23X17.h>
#include "globals.h"


class MCP23X17 {
	public:
		static const char* PIN_NAMES[16];
		static const char* PIN_VALUES[2];
	private:
		uint8_t            status;
		TwoWire            wire;
		Adafruit_MCP23X17  mcp23X17;
		uint16_t           mcp23X17_gpio_values;
	public:
		MCP23X17();
		void init(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl);
		void config_inputs(const char* device_type, const char* device_name, JSONVar& inputs, JSONVar& actions);
		void config_outputs(const char* device_type, const char* device_name, JSONVar& outputs);

		void start();
		void check();
	protected:
		static void loop();
};

#endif

