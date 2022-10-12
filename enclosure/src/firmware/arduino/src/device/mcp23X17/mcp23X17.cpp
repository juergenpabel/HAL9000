#include <Adafruit_MCP23X17.h>
#include <ArduinoJson.h>

#include "gui/overlay/overlay.h"
#include "device/mcp23X17/devices.h"
#include "device/mcp23X17/mcp23X17.h"
#include "globals.h"

static MCP23X17_Switch      g_devices_switch[2];
static MCP23X17_Button      g_devices_button[2];
static MCP23X17_Toggle      g_devices_toggle[2];
static MCP23X17_Rotary      g_devices_rotary[2];
static MCP23X17_DigitalOut  g_devices_digitalout[2];

etl::string<2> MCP23X17::PIN_NAMES[16] = {"A0","A1","A2","A3","A4","A5","A6","A7","B0","B1","B2","B3","B4","B5","B6","B7"};
etl::string<4> MCP23X17::PIN_VALUES[2] = {MCP23X17_PIN_VALUE_LOW, MCP23X17_PIN_VALUE_HIGH};

#define MCP23X17_STATE_UNINITIALIZED 0x10
#define MCP23X17_STATE_INITIALIZED   0x20
#define MCP23X17_STATE_RUNNING       0x30

 
MCP23X17::MCP23X17()
         :status(MCP23X17_STATE_UNINITIALIZED),
          mcp23X17() {
}


void MCP23X17::init() {
	int i2c_address = SYSTEM_SETTINGS_MCP23X17_ADDRESS;
	int i2c_pin_sda = TWOWIRE_PIN_SDA;
	int i2c_pin_scl = TWOWIRE_PIN_SCL;

	if(g_system_settings.count("device/mcp23X17:i2c/address") == 1) {
		i2c_address = atoi(g_system_settings["device/mcp23X17:i2c/address"].c_str());
	}
	if(g_system_settings.count("device/mcp23X17:i2c/pin-sda") == 1) {
		i2c_pin_sda = atoi(g_system_settings["device/mcp23X17:i2c/pin-sda"].c_str());
	}
	if(g_system_settings.count("device/mcp23X17:i2c/pin-scl") == 1) {
		i2c_pin_scl = atoi(g_system_settings["device/mcp23X17:i2c/pin-scl"].c_str());
	}
	this->init(i2c_address, i2c_pin_sda, i2c_pin_scl);

}


void MCP23X17::init(uint8_t i2c_addr, uint8_t pin_sda, uint8_t pin_scl) {
	TwoWire* twowire = nullptr;

	if(this->status != MCP23X17_STATE_UNINITIALIZED) {
		g_util_webserial.send("syslog/warn", "MCP23X17 already initialized");
		return;
	}
	twowire = g_device_microcontroller.twowire_get(0, pin_sda, pin_scl);
	if(twowire == nullptr) {
		g_util_webserial.send("syslog/error", "MCP23X17 could not obtain TwoWire instance");
		return;
	}
	if(this->mcp23X17.begin_I2C(i2c_addr, twowire) == false) {
		g_util_webserial.send("syslog/error", "MCP23X17 failed to initialize");
		return;
	}
	this->mcp23X17.setupInterrupts(false, true, LOW);
	this->status = MCP23X17_STATE_INITIALIZED;
}


void MCP23X17::config_inputs(const etl::string<GLOBAL_VALUE_SIZE>& device_type, const etl::string<GLOBAL_VALUE_SIZE>& device_name, const JsonArray& inputs, const JsonObject& events) {
	MCP23X17_InputDevice* device = nullptr;

	if(this->status == MCP23X17_STATE_UNINITIALIZED) {
		this->init();
	}
	if(this->status == MCP23X17_STATE_RUNNING) {
		g_util_webserial.send("syslog/error", "MCP23X17 already loop()'ing on the other core");
		return;
	}
	if(device_type.size() == 0 || device_name.size() == 0) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_inputs(): invalid parameters name/type");
		g_util_webserial.send("syslog/error", device_type);
		g_util_webserial.send("syslog/error", device_name);
		return;
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
	if(device_type.compare("toggle") == 0) {
		for(int i=0;i<3;i++) {
			if(device == nullptr && g_devices_toggle[i].isConfigured() == false) {
				device = &g_devices_toggle[i];
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
		return;
	}
	if(device->configure(device_name, &this->mcp23X17, inputs, events) == false) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_inputs(): device configuration failed");
		return;
	}
}


void MCP23X17::config_outputs(const etl::string<GLOBAL_VALUE_SIZE>& device_type, const etl::string<GLOBAL_VALUE_SIZE>& device_name, const JsonArray& outputs) {
	MCP23X17_OutputDevice* device = nullptr;

	if(this->status == MCP23X17_STATE_UNINITIALIZED) {
		this->init();
	}
	if(device_type.size() == 0 || device_name.size() == 0) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_outputs(): invalid parameters name/type");
		g_util_webserial.send("syslog/error", device_type);
		g_util_webserial.send("syslog/error", device_name);
		return;
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
		return;
	}
	if(device->configure(device_name, &this->mcp23X17, outputs) == false) {
		g_util_webserial.send("syslog/error", "MCP23X17::config_outputs(): device configuration failed");
		return;
	}
}


void MCP23X17::check() {
	uint16_t mcp23X17_gpio_values = 0;

	if(this->status != MCP23X17_STATE_RUNNING) {
		return;
	}
	mcp23X17_gpio_values = this->mcp23X17.readGPIOAB();
	if(mcp23X17_gpio_values != this->mcp23X17_gpio_values) {

		for(int nr=0; nr<16; nr++) {
			uint8_t old_value = 0;
			uint8_t new_value = 0;

			old_value = (this->mcp23X17_gpio_values >> nr) & 0x01;
			new_value = (      mcp23X17_gpio_values >> nr) & 0x01;
			if(old_value != new_value) {
				for(uint8_t i=0; i<SYSTEM_SETTINGS_MCP23X17_DEVICES; i++) {
					MCP23X17_Device*      device;
					MCP23X17_InputDevice* input_device;

					device = MCP23X17_Device::instances[i];
					if(device != nullptr) {
						if(device->isInputDevice() == true) {
							static StaticJsonDocument<1024> data;

							data.clear();
							input_device = (MCP23X17_InputDevice*)device;
							input_device->process(MCP23X17::PIN_NAMES[nr], MCP23X17::PIN_VALUES[new_value], data);
							if(data.size() > 0) {
								g_util_webserial.send("device/event", data);
							}
						}
					}
				}
			}
		}
		this->mcp23X17_gpio_values = mcp23X17_gpio_values;
	}
}


void MCP23X17::start() {
	if(this->status != MCP23X17_STATE_INITIALIZED) {
		g_util_webserial.send("syslog/warn", "MCP23X17::start() with invalid state");
		return;
	}
	this->mcp23X17_gpio_values = this->mcp23X17.readGPIOAB();
	this->status = MCP23X17_STATE_RUNNING;
	g_device_microcontroller.thread_create(MCP23X17::loop, 1);
}


void MCP23X17::loop() {
	g_util_webserial.send("syslog/debug", "MCP23X17::loop() now running on 2nd core");
	while(true) {
		g_device_mcp23X17.check();
		yield();
		delay(1);
	}
}

