#include <Adafruit_MCP23X17.h>
#include <Wire.h>
#include <string.h>
#include "mcp23017.h"


Adafruit_MCP23X17 g_mcp23017;
static TwoWire    g_wire(i2c0, 0, 1);
static char       g_pin_names[16][MaximumKeyNameLength] = {0};
static boolean    g_initialized = false;
static uint8_t    g_interrupt_pin = 0xff;
static uint8_t    g_interrupt_val = 0;

void mcp23017_begin(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl) {
	if(g_initialized) {
		g_webserial.warn("MCP23017 already initialized");
		return;
	}
	g_wire.setSDA(pin_sda);
	g_wire.setSCL(pin_scl);
	if(!g_mcp23017.begin_I2C(i2c_addr, &g_wire)) {
		g_webserial.warn("MCP23017 failed to initialize");
		return;
	}
	g_mcp23017.setupInterrupts(false, false, LOW);
	pinMode(MCP23017_INTA, INPUT);
	pinMode(MCP23017_INTB, INPUT);
	g_initialized = true;
}


void mcp23017_config_inputs(const char* name, const char* pin) {
	int pin_number = -1;

	if(!g_initialized) {
		g_webserial.warn("MCP23017 not initialized");
		return;
	}
	if(name == NULL || pin == NULL || strnlen(pin, 3) != 2) {
		g_webserial.warn("mcp23017_config_inputs(): invalid parameters name/pin");
		g_webserial.warn(name);
		g_webserial.warn(pin);
		return;
	}
	if((pin[0] != 'A' && pin[0] != 'B') || pin[1] < 0x30 || pin[1] > 0x39) {
		g_webserial.warn("mcp23017_config_inputs(): invalid pin (A0-A7,B0-B7)");
		g_webserial.warn(pin);
		return;
	}
	pin_number = pin[0] - 'A' + pin[1] - '0';
	strncpy(g_pin_names[pin_number], name, MaximumKeyNameLength-1);
	g_mcp23017.pinMode(pin_number, INPUT_PULLUP);
	g_mcp23017.setupInterruptPin(pin_number, LOW);
}


void mcp23017_check() {
	uint8_t  interrupt_pin = 0;
	uint8_t  interrupt_val = 0;

	if(!g_initialized) {
		return;
	}
	interrupt_pin = g_mcp23017.getLastInterruptPin();
	if(interrupt_pin == 0xff) {
		return;
	}
	interrupt_val = g_mcp23017.digitalRead(interrupt_pin);
	if(interrupt_pin != g_interrupt_pin || (interrupt_pin == g_interrupt_pin && interrupt_val != g_interrupt_val)) {
		JSONVar data;

		data["pin"] = interrupt_pin;
		data["status"] = interrupt_val ? "HIGH" : "LOW";
		g_webserial.send("mcp23017:interrupt", data);
		g_interrupt_pin = interrupt_pin;
		g_interrupt_val = interrupt_val;
	}
}

