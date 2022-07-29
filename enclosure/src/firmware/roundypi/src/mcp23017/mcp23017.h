#include "globals.h"
#include <Adafruit_MCP23X17.h>

extern Adafruit_MCP23X17 g_mcp23017;

void mcp23017_config_i2c(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl);
void mcp23017_config_inputs(const char* event_name, const char* pin_name, const char* event_state);
void mcp23017_config_outputs(char* pin_name, const char* pin_state);
void mcp23017_set_core(uint8_t core_nr);

void mcp23017_check(uint8_t core_nr);

