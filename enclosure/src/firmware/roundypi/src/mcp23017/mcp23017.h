#include "globals.h"
#include <Adafruit_MCP23X17.h>

extern Adafruit_MCP23X17 g_mcp23017;

void mcp23017_begin(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl);
void mcp23017_check();
void mcp23017_config_inputs(const char* name, const char* value);

