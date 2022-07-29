#include <Adafruit_MCP23X17.h>
#include <Wire.h>
#include <string.h>
#include "mcp23017.h"


Adafruit_MCP23X17 g_mcp23017;
static TwoWire    g_wire(i2c0, 0, 1);
static char       g_event_names[16][MaximumKeyNameLength] = {0};
static uint8_t    g_event_states[16] = { 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff };
static uint8_t    g_interrupt_pin = 0xff;
static uint8_t    g_interrupt_val = 0x00;

static boolean    g_initialized = false;
static uint8_t    g_running_on_core = 0;


void mcp23017_config_i2c(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl) {
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


void mcp23017_config_inputs(const char* event_name, const char* pin_name, const char* event_state) {
	int pin_number = -1;

	if(!g_initialized) {
		mcp23017_config_i2c(0x20, 0, 1);
	}
	if(g_running_on_core > 0) {
		g_webserial.warn("MCP23017 already running in loop()");
		return;
	}
	if(event_name == NULL || pin_name == NULL || strnlen(pin_name, 3) != 2) {
		g_webserial.warn("mcp23017_config_inputs(): invalid parameters name/pin");
		g_webserial.warn(event_name);
		g_webserial.warn(pin_name);
		return;
	}
	if((pin_name[0] != 'A' && pin_name[0] != 'B') || pin_name[1] < 0x30 || pin_name[1] > 0x39) {
		g_webserial.warn("mcp23017_config_inputs(): invalid pin (A0-A7,B0-B7)");
		g_webserial.warn(pin_name);
		return;
	}
	pin_number = (pin_name[0] - 'A') * 8 + pin_name[1] - '0';
	strncpy(&g_event_names[pin_number][0], event_name, MaximumKeyNameLength-1);
	g_event_states[pin_number] = 0xff;
	if(event_state != NULL) {
		if(strncmp(event_state, "LOW", 4) == 0) {
			g_event_states[pin_number] = 0;
		}
		if(strncmp(event_state, "HIGH", 5) == 0) {
			g_event_states[pin_number] = 1;
		}
	}
	g_mcp23017.pinMode(pin_number, INPUT_PULLUP);
	g_mcp23017.setupInterruptPin(pin_number, LOW);
}


void mcp23017_config_outputs(const char* pin_name, const char* pin_state) {
	if(!g_initialized) {
		mcp23017_config_i2c(0x20, 0, 1);
	}
	if(g_running_on_core > 0) {
		g_webserial.warn("MCP23017 already running in loop()");
		return;
	}
}


void mcp23017_set_core(uint8_t core_nr) {
	if(g_running_on_core == 0) {
		g_running_on_core = core_nr;
	}
}


void mcp23017_check(uint8_t core_nr) {
	uint8_t  interrupt_pin = 0;
	uint8_t  interrupt_val = 0;

	if(core_nr != g_running_on_core) {
		return;
	}
	interrupt_pin = g_mcp23017.getLastInterruptPin();
	if(interrupt_pin == 0xff) {
		return;
	}
	interrupt_val = g_mcp23017.digitalRead(interrupt_pin);
	if(interrupt_pin != g_interrupt_pin || (interrupt_pin == g_interrupt_pin && interrupt_val != g_interrupt_val)) {
		if(g_event_states[interrupt_pin] == 0xff || g_event_states[interrupt_pin] == interrupt_val) {
			JSONVar data;

			data["event"] = g_event_names[interrupt_pin];
			data["input"] = JSONVar();
			data["input"]["pin"] = interrupt_pin;
			data["input"]["status"] = interrupt_val ? "HIGH" : "LOW";
			g_webserial.send("mcp23017:event", data);
		}
		g_interrupt_pin = interrupt_pin;
		g_interrupt_val = interrupt_val;
	}
}

