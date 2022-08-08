#include <Adafruit_MCP23X17.h>
#include <Wire.h>
#include <string.h>
#include <RingBuf.h>
#include <JSONVar.h>
#include <pico/multicore.h>
#include "gui/overlay/overlay.h"
#include "device/mcp23X17/devices.h"
#include "device/mcp23X17/mcp23X17.h"


static MCP23X17_Switch g_devices_switch[2];
static MCP23X17_Button g_devices_button[2];
static MCP23X17_Toggle g_devices_toggle[2];
static MCP23X17_Rotary g_devices_rotary[2];

const char* MCP23X17::PIN_NAMES[16] = {"A0","A1","A2","A3","A4","A5","A6","A7","B0","B1","B2","B3","B4","B5","B6","B7"};
const char* MCP23X17::PIN_VALUES[2] = {"LOW", "HIGH"};

#define MCP23X17_STATE_UNINITIALIZED 0x10
#define MCP23X17_STATE_INITIALIZED   0x20
#define MCP23X17_STATE_RUNNING       0x30

 
MCP23X17::MCP23X17() : status(MCP23X17_STATE_UNINITIALIZED), wire(i2c0, 0, 1), mcp23X17() {
}


void MCP23X17::init(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl) {
	if(this->status != MCP23X17_STATE_UNINITIALIZED) {
		g_webserial.send("syslog", "MCP23X17 already initialized");
		return;
	}
	this->wire.setSDA(pin_sda);
	this->wire.setSCL(pin_scl);
	if(this->mcp23X17.begin_I2C(i2c_addr, &this->wire) == false) {
		g_webserial.send("syslog", "MCP23X17 failed to initialize");
		return;
	}
	this->mcp23X17.setupInterrupts(false, true, LOW);
	pinMode(MCP23X17_INTA, INPUT_PULLUP);
	pinMode(MCP23X17_INTB, INPUT_PULLUP);
	this->status = MCP23X17_STATE_INITIALIZED;
}


void MCP23X17::config_inputs(const char* event_name, const char* device_type, JSONVar& inputs, JSONVar& actions) {
	MCP23X17_Device* device = NULL;

	if(this->status == MCP23X17_STATE_UNINITIALIZED) {
		this->init(0x20, 0, 1);
	}
	if(this->status == MCP23X17_STATE_RUNNING) {
		g_webserial.send("syslog", "MCP23X17 already loop()'ing on the other core");
		return;
	}
	if(event_name == NULL || device_type == NULL) {
		g_webserial.send("syslog", "MCP23X17::config_inputs(): invalid parameters name/type");
		g_webserial.send("syslog", event_name);
		g_webserial.send("syslog", device_type);
		return;
	}
	if(strncmp(device_type, "switch", 7) == 0) {
		for(int i=0;i<3;i++) {
			if(device == NULL && g_devices_switch[i].isConfigured() == false) {
				device = &g_devices_switch[i];
			}
		}
	}
	if(strncmp(device_type, "button", 7) == 0) {
		for(int i=0;i<3;i++) {
			if(device == NULL && g_devices_button[i].isConfigured() == false) {
				device = &g_devices_button[i];
			}
		}
	}
	if(strncmp(device_type, "toggle", 7) == 0) {
		for(int i=0;i<3;i++) {
			if(device == NULL && g_devices_toggle[i].isConfigured() == false) {
				device = &g_devices_toggle[i];
			}
		}
	}
	if(strncmp(device_type, "rotary", 7) == 0) {
		for(int i=0;i<3;i++) {
			if(device == NULL && g_devices_rotary[i].isConfigured() == false) {
				device = &g_devices_rotary[i];
			}
		}
	}
	if(device == NULL) {
		g_webserial.send("syslog", "MCP23X17::config_inputs(): invalid parameter device_type");
		g_webserial.send("syslog", device_type);
		return;
	}
	if(device->configure(event_name, &this->mcp23X17, inputs, actions) == false) {
		g_webserial.send("syslog", "MCP23X17::config_inputs(): device configuration failed");
		g_webserial.send("syslog", inputs);
		return;
	}
}


void MCP23X17::config_outputs(const char* event_name, const char* device_type, JSONVar& outputs) {
	MCP23X17_Device* device = NULL;

	if(this->status == MCP23X17_STATE_UNINITIALIZED) {
		this->init(0x20, 0, 1);
	}
	if(event_name == NULL || device_type == NULL) {
		g_webserial.send("syslog", "MCP23X17::config_outputs(): invalid parameters name/type");
		g_webserial.send("syslog", event_name);
		g_webserial.send("syslog", device_type);
		return;
	}
	if(strncmp(device_type, "TODO", 5) == 0) {
		//TODO:device = &g_devices_switch[0];
	}
	if(device == NULL) {
		g_webserial.send("syslog", "MCP23X17::config_outputs(): invalid parameter device_type");
		g_webserial.send("syslog", device_type);
		return;
	}
//TODO	while(device->isConfigured()) {
//TODO		device += 1;
//TODO	}
//TODO	if(device->configure(event_name, &this->mcp23X17, outputs) == false) {
//TODO		g_webserial.send("syslog", "MCP23X17::config_outputs(): device configuration failed");
//TODO		g_webserial.send("syslog", outputs);
//TODO		return;
//TODO	}
}


void MCP23X17::check() {
	uint16_t mcp23X17_gpio_values = 0;

	if(this->status != MCP23X17_STATE_RUNNING) {
		return;
	}
	mcp23X17_gpio_values = this->mcp23X17.readGPIOAB();
	if(mcp23X17_gpio_values != this->mcp23X17_gpio_values) {

		for(int pin=0; pin<16; pin++) {
			uint8_t old_value = 0;
			uint8_t new_value = 0;

			old_value = (this->mcp23X17_gpio_values >> pin) & 0x01;
			new_value = (      mcp23X17_gpio_values >> pin) & 0x01;
			if(old_value != new_value) {
				const char*  pin_label = NULL;
				const char*  pin_value = NULL;

				pin_label = MCP23X17::PIN_NAMES[pin];
				pin_value = MCP23X17::PIN_VALUES[new_value];
				for(uint8_t i=0; i<MCP23X17_INSTANCES; i++) {
					MCP23X17_Device* device;

					device = MCP23X17_Device::instances[i];
					if(device != NULL) {
						if(device->isConfigured()) {
							static JSONVar data;

							data = device->process(pin_label, pin_value);
							if(data.length() > 0 || data.keys().length() > 0) {
								g_webserial_queue.pushMessage("device/event", data);
							}
						}
					}
				}
			}
		}
		this->mcp23X17_gpio_values = mcp23X17_gpio_values;
	}
}


void MCP23X17::loop() {
	MCP23X17* mcp23X17 = NULL;
	
	mcp23X17 = (MCP23X17*)multicore_fifo_pop_blocking();
	g_webserial_queue.pushMessage("syslog", "MCP23X17::loop() now running on 2nd core");
	while(true) {
		mcp23X17->check();
		yield();
		sleep_ms(1);
	}
}


void MCP23X17::start() {
	if(this->status != MCP23X17_STATE_INITIALIZED) {
		g_webserial.send("syslog", "MCP23X17::start() with invalid state");
		return;
	}
	this->mcp23X17_gpio_values = this->mcp23X17.readGPIOAB();
	this->status = MCP23X17_STATE_RUNNING;
	multicore_launch_core1(MCP23X17::loop);
	multicore_fifo_push_blocking((uint32_t)this);
}

