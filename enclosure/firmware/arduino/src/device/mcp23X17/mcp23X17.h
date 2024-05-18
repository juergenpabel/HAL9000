#ifndef __ROUNDYPI_MCP23X17_H__
#define __ROUNDYPI_MCP23X17_H__

#include <Adafruit_MCP23X17.h>
#include <ArduinoJson.h>
#include <etl/string.h>

#define MCP23X17_PIN_NAMES_COUNT 16
#define MCP23X17_PIN_NAMES_SIZE 2
#define MCP23X17_PIN_VALUES_COUNT  2
#define MCP23X17_PIN_VALUES_SIZE  4

#define MCP23X17_PIN_VALUE_LOW  "LOW"
#define MCP23X17_PIN_VALUE_HIGH "HIGH"


class MCP23X17 {
	friend class MCP23X17_Rotary;
	friend class MCP23X17_Switch;
	friend class MCP23X17_Button;
	friend class MCP23X17_OutputDevice;
	friend class MCP23X17_DigitalOut;
	protected:
		static etl::string<MCP23X17_PIN_NAMES_SIZE>  PIN_NAMES[MCP23X17_PIN_NAMES_COUNT];
		static etl::string<MCP23X17_PIN_VALUES_SIZE> PIN_VALUES[MCP23X17_PIN_VALUES_COUNT];
	private:
		uint8_t            status;
		Adafruit_MCP23X17  mcp23X17;
		uint16_t           mcp23X17_gpio_values;
	public:
		MCP23X17();
		void init();
		void init(uint8_t i2c_bus, uint8_t i2c_addr);
		void config_inputs(const etl::string<GLOBAL_KEY_SIZE>& device_type, const etl::string<GLOBAL_KEY_SIZE>& device_name, const JsonArray& inputs, const JsonObject& status);
		void config_outputs(const etl::string<GLOBAL_KEY_SIZE>& device_type, const etl::string<GLOBAL_KEY_SIZE>& device_name, const JsonArray& outputs);

		void start();
		void check();
	protected:
		static void loop();
};

#endif

