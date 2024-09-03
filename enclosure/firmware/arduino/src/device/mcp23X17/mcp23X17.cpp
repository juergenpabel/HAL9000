#include <Adafruit_MCP23X17.h>
#include <ArduinoJson.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/overlay/overlay.h"
#include "device/mcp23X17/devices.h"
#include "device/mcp23X17/mcp23X17.h"
#include "globals.h"

static MCP23X17_Switch      g_devices_switch[2];
static MCP23X17_Button      g_devices_button[2];
static MCP23X17_Rotary      g_devices_rotary[2];
static MCP23X17_DigitalOut  g_devices_digitalout[2];

etl::string<2> MCP23X17::PIN_NAMES[16] = {"A0","A1","A2","A3","A4","A5","A6","A7","B0","B1","B2","B3","B4","B5","B6","B7"};
etl::string<4> MCP23X17::PIN_VALUES[2] = {MCP23X17_PIN_VALUE_LOW, MCP23X17_PIN_VALUE_HIGH};

#define MCP23X17_STATE_UNINITIALIZED 0x10
#define MCP23X17_STATE_INITIALIZED   0x20
#define MCP23X17_STATE_RUNNING       0x30
#define MCP23X17_STATE_RUNNING_MAIN  0x31
#define MCP23X17_STATE_RUNNING_TASK  0x32

 
MCP23X17::MCP23X17()
         :status(MCP23X17_STATE_UNINITIALIZED),
          mcp23X17() {
}


bool MCP23X17::init() {
	int i2c_bus     = 0;
	int i2c_address = 0;

	if(g_application.hasSetting("device/mcp23X17:i2c/bus") == true) {
		i2c_bus = atoi(g_application.getSetting("device/mcp23X17:i2c/bus").c_str());
	}
	if(g_application.hasSetting("device/mcp23X17:i2c/address") == true) {
		i2c_address = atoi(g_application.getSetting("device/mcp23X17:i2c/address").c_str());
	}
	return this->init(i2c_bus, i2c_address);
}


bool MCP23X17::init(uint8_t i2c_bus, uint8_t i2c_addr) {
	TwoWire* twowire = nullptr;

	if(this->status != MCP23X17_STATE_UNINITIALIZED) {
		g_util_webserial.send("syslog/warn", "MCP23X17 already initialized");
		return false;
	}
	twowire = g_device_microcontroller.twowire_get(i2c_bus);
	if(twowire == nullptr) {
		g_util_webserial.send("syslog/error", "MCP23X17 could not obtain TwoWire instance");
		return false;
	}
	if(this->mcp23X17.begin_I2C(i2c_addr, twowire) == false) {
		g_util_webserial.send("syslog/error", "MCP23X17 failed to initialize");
		return false;
	}
	this->status = MCP23X17_STATE_INITIALIZED;
	return true;
}


bool MCP23X17::config_inputs(const etl::string<GLOBAL_KEY_SIZE>& device_type, const etl::string<GLOBAL_KEY_SIZE>& device_name, const JsonArray& inputs, const JsonObject& events) {
	MCP23X17_InputDevice* device = nullptr;

	if(this->status == MCP23X17_STATE_UNINITIALIZED) {
		this->init();
	}
	if((this->status & MCP23X17_STATE_RUNNING) == MCP23X17_STATE_RUNNING) {
		g_util_webserial.send("syslog/error", "MCP23X17 already started, configuration of inputs not possible any more");
		return false;
	}
	if(device_type.size() == 0 || device_name.size() == 0) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_inputs(): invalid parameters name/type");
		g_util_webserial.send("syslog/error", device_type);
		g_util_webserial.send("syslog/error", device_name);
		return false;
	}
	if(device_type.compare("switch") == 0) {
		for(int i=0;i<3;i++) {
			if(device == nullptr && g_devices_switch[i].isConfigured() == false) {
				device = &g_devices_switch[i];
			}
		}
	}
	if(device_type.compare("button") == 0) {
		for(int i=0;i<3;i++) {
			if(device == nullptr && g_devices_button[i].isConfigured() == false) {
				device = &g_devices_button[i];
			}
		}
	}
	if(device_type.compare("rotary") == 0) {
		for(int i=0;i<3;i++) {
			if(device == nullptr && g_devices_rotary[i].isConfigured() == false) {
				device = &g_devices_rotary[i];
			}
		}
	}
	if(device == nullptr) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_inputs(): invalid parameter device_type");
		g_util_webserial.send("syslog/error", device_type);
		return false;
	}
	if(device->configure(device_name, &this->mcp23X17, inputs, events) == false) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_inputs(): device configuration failed");
		return false;
	}
	return true;
}


bool MCP23X17::config_outputs(const etl::string<GLOBAL_KEY_SIZE>& device_type, const etl::string<GLOBAL_KEY_SIZE>& device_name, const JsonArray& outputs) {
	MCP23X17_OutputDevice* device = nullptr;

	if(this->status == MCP23X17_STATE_UNINITIALIZED) {
		this->init();
	}
	if((this->status & MCP23X17_STATE_RUNNING) == MCP23X17_STATE_RUNNING) {
		g_util_webserial.send("syslog/error", "MCP23X17 already started, configuration of outputs not possible any more");
		return false;
	}
	if(device_type.size() == 0 || device_name.size() == 0) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_outputs(): invalid parameters name/type");
		g_util_webserial.send("syslog/error", device_type);
		g_util_webserial.send("syslog/error", device_name);
		return false;
	}
	if(device_type.compare("digital") == 0) {
		for(int i=0;i<3;i++) {
			if(device == nullptr && g_devices_digitalout[i].isConfigured() == false) {
				device = &g_devices_digitalout[i];
			}
		}
	}
	if(device == nullptr) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_outputs(): invalid parameter device_type");
		g_util_webserial.send("syslog/error", device_type);
		return false;
	}
	if(device->configure(device_name, &this->mcp23X17, outputs) == false) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_outputs(): device configuration failed");
		return false;
	}
	return true;
}


bool MCP23X17::start(bool run_as_task) {
	bool result = false;

	if(this->status != MCP23X17_STATE_INITIALIZED) {
		g_util_webserial.send("syslog/warn", "MCP23X17::start() called with invalid state (BUG)");
		return false;
	}
	g_device_microcontroller.mutex_enter("gpio");
	this->mcp23X17_gpio_values = this->mcp23X17.readGPIOAB();
	g_device_microcontroller.mutex_leave("gpio");
	switch(run_as_task) {
		case true:
			result = g_device_microcontroller.task_create("MCP23X17", MCP23X17::loop, 1);
			if(result == true) {
				g_util_webserial.send("syslog/debug", "MCP23X17::loop() started on 2nd core");
				this->status = MCP23X17_STATE_RUNNING_TASK;
			} else {
				g_util_webserial.send("syslog/warn", "MCP23X17::loop() failed to start task on 2nd core, falling back to invocations from loop()");
				this->status = MCP23X17_STATE_RUNNING_MAIN;
				result = true;
			}
			break;
		case false:
			this->status = MCP23X17_STATE_RUNNING_MAIN;
			result = true;
			break;
	}
	return result;
}


void MCP23X17::loop() {
	unsigned long millis_before = 0;
	unsigned long millis_after = 0;
	unsigned long millis_measured = 0;
	unsigned long counts_measured = 0;

	g_util_webserial.send("syslog/debug", "MCP23X17::loop() now running on 2nd core");
	while(true) {
		millis_before = millis();
		g_device_mcp23X17.check(true);
		yield();
		millis_after = millis();
		if((millis_after-millis_before) < MCP23X17_POLLING_INTERVAL_MS) {
			unsigned long millis_target;

			millis_target = millis_after + (MCP23X17_POLLING_INTERVAL_MS-(millis_after-millis_before));
			while(millis() < millis_target) {
				delay(1);
			}
		}
		counts_measured += 1;
		millis_measured += millis_after-millis_before;
		if(millis_measured >= 60000UL) {
			static etl::string<GLOBAL_VALUE_SIZE> log_message;

			log_message = "MCP23X17::loop() average ms per iteration: ";
			etl::to_string(((float)millis_measured)/counts_measured, log_message, etl::format_spec().precision(1), true);
			g_util_webserial.send("syslog/debug", log_message);
			counts_measured = 0;
			millis_measured = 0;
		}
	}
}


void MCP23X17::check(bool from_task) {
	static unsigned long millis_previous = 0;
	       unsigned long millis_current = 0;
	       uint16_t      mcp23X17_gpio_values = 0;

	if((this->status & MCP23X17_STATE_RUNNING) != MCP23X17_STATE_RUNNING) {
		return;
	}
	if(from_task == false && this->status == MCP23X17_STATE_RUNNING_TASK) {
		return;
	}
	millis_current = millis();
	if((millis_current-millis_previous) < MCP23X17_POLLING_INTERVAL_MS) {
		return;
	}
	millis_previous = millis_current;
	g_device_microcontroller.mutex_enter("gpio");
	mcp23X17_gpio_values = this->mcp23X17.readGPIOAB();
	g_device_microcontroller.mutex_leave("gpio");
	if(mcp23X17_gpio_values != this->mcp23X17_gpio_values) {

		for(int nr=0; nr<16; nr++) {
			uint8_t old_value = 0;
			uint8_t new_value = 0;

			old_value = (this->mcp23X17_gpio_values >> nr) & 0x01;
			new_value = (      mcp23X17_gpio_values >> nr) & 0x01;
			if(old_value != new_value) {
				for(uint8_t i=0; i<APPLICATION_CONFIGURATION_MCP23X17_DEVICES; i++) {
					MCP23X17_Device*      device;
					MCP23X17_InputDevice* input_device;

					device = MCP23X17_Device::instances[i];
					if(device != nullptr) {
						if(device->isInputDevice() == true) {
							static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> json;

							json.clear();
							input_device = (MCP23X17_InputDevice*)device;
							input_device->process(MCP23X17::PIN_NAMES[nr], MCP23X17::PIN_VALUES[new_value], json);
							if(json.size() > 0) {
								g_util_webserial.send("device/input", json);
							}
						}
					}
				}
			}
		}
		this->mcp23X17_gpio_values = mcp23X17_gpio_values;
	}
}

