#ifdef ARDUINO_ARCH_RP2040

#include <hardware/watchdog.h>
#include <hardware/structs/watchdog.h>
#include <hardware/resets.h>
#include <pico/bootrom.h>
#include <pico/multicore.h>
#include <Wire.h>
#include <etl/string.h>

#include "device/microcontroller/rp2040.h"
#include "globals.h"

Microcontroller::Microcontroller()
                :AbstractMicrocontroller("rp2040")
                ,mutex_map()
                ,twowire_init{false, false}
                ,twowire_data{TwoWire(i2c0,0,0), TwoWire(i2c1,0,0)} {
}


void Microcontroller::start(uint32_t& timestamp) {
	if(watchdog_hw->scratch[5] == 0x00002001) {
		timestamp = watchdog_hw->scratch[7];
		watchdog_hw->scratch[5] = 0x00000000;
		watchdog_hw->scratch[6] = 0x00000000;
		watchdog_hw->scratch[7] = 0x00000000;
	}
}


bool Microcontroller::configure(const JsonVariant& configuration) {
	static etl::string<GLOBAL_VALUE_SIZE> error_details;
	       uint8_t pin_sda;
	       uint8_t pin_scl;

	error_details.clear();
	if(configuration.containsKey("i2c") == false) {
		error_details = "board configuration does not include an 'i2c' configuration section";
	} else {
		if(configuration["i2c"].containsKey("i2c-0") == false && configuration["i2c"].containsKey("i2c-1") == false) {
			error_details = "board configuration does not include either an 'i2c-0' or 'i2c-1' configuration section";
		}
	}
	if(error_details.empty() == true) {
		if(configuration["i2c"].containsKey("i2c-0") == true) {
			if(configuration["i2c"]["i2c-0"].containsKey("pin-sda") == true && configuration["i2c"]["i2c-0"].containsKey("pin-scl") == true) {
				pin_sda = configuration["i2c"]["i2c-0"]["pin-sda"].as<unsigned char>();
				pin_scl = configuration["i2c"]["i2c-0"]["pin-scl"].as<unsigned char>();
				this->twowire_data[0].setSDA(pin_sda);
				this->twowire_data[0].setSCL(pin_scl);
				this->twowire_init[0] = true;
			} else {
				error_details = "board configuration for 'i2c-0' is missing 'pin-sda' and/or 'pin-scl' options";
			}
		}
		if(configuration["i2c"].containsKey("i2c-1") == true) {
			if(configuration["i2c"]["i2c-1"].containsKey("pin-sda") == true && configuration["i2c"]["i2c-1"].containsKey("pin-scl") == true) {
				pin_sda = configuration["i2c"]["i2c-1"]["pin-sda"].as<unsigned char>();
				pin_scl = configuration["i2c"]["i2c-1"]["pin-scl"].as<unsigned char>();
				this->twowire_data[1].setSDA(pin_sda);
				this->twowire_data[1].setSCL(pin_scl);
				this->twowire_init[1] = true;
			} else {
				error_details = "board configuration for 'i2c-1' is missing 'pin-sda' and/or 'pin-scl' options";
			}
		}
	}
	if(error_details.empty() == false) {
		g_system_application.processError("panic", "213", "Board error", error_details);
		return false;
	}
	return true;
}


void Microcontroller::reset(uint32_t timestamp) {
	if(timestamp > 0) {
		hw_clear_bits(&watchdog_hw->ctrl, WATCHDOG_CTRL_ENABLE_BITS);
		watchdog_hw->scratch[5] = 0x00002001;
		watchdog_hw->scratch[6] = 0x00000000;
		watchdog_hw->scratch[7] = timestamp;
	}
	multicore_reset_core1();
	reset_block(RESETS_RESET_SPI0_BITS | RESETS_RESET_SPI1_BITS);
	unreset_block_wait(RESETS_RESET_SPI0_BITS | RESETS_RESET_SPI1_BITS);
	reset_block(RESETS_RESET_I2C0_BITS | RESETS_RESET_I2C1_BITS);
	unreset_block_wait(RESETS_RESET_I2C0_BITS | RESETS_RESET_I2C1_BITS);
	reset_block(RESETS_RESET_IO_BANK0_BITS);
	unreset_block_wait(RESETS_RESET_IO_BANK0_BITS);
	reset_block(RESETS_RESET_USBCTRL_BITS);
	unreset_block_wait(RESETS_RESET_USBCTRL_BITS);
	watchdog_reboot(0, 0, 0);
}


void Microcontroller::reset_uf2() {
	multicore_reset_core1();
	reset_usb_boot(0, 0);
}


void Microcontroller::halt() {
	multicore_reset_core1();
	while(true) {
		sleep_ms(1);
	}
}


bool Microcontroller::mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 0) {
		if(this->mutex_map.size() < this->mutex_map.capacity()) {
			this->mutex_map[name] = {0};
			mutex_init(&this->mutex_map[name]);
			result = true;
		}
	}
	return result;
}


bool Microcontroller::mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		result = ::mutex_try_enter(&this->mutex_map[name], nullptr);
	}
	return result;
}


bool Microcontroller::mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		mutex_enter_blocking(&this->mutex_map[name]);
		result = true;
	}
	return result;
}


bool Microcontroller::mutex_leave(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		mutex_exit(&this->mutex_map[name]);
		result = true;
	}
	return result;
}


bool Microcontroller::mutex_destroy(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		this->mutex_map.erase(name);
		result = true;
	}
	return result;
}



TwoWire* Microcontroller::twowire_get(uint8_t instance) {
	if(instance >= 2 || this->twowire_init[instance] == false) {
		return nullptr;
	}
	return &this->twowire_data[instance];
}


bool Microcontroller::task_create(const etl::string<GLOBAL_KEY_SIZE>& task_name, void (*task_function)(), uint8_t core) {
	bool result = false;

	if(core == 1) {
		g_util_webserial.send("syslog/warn", "Microcontroller::task_create() disabled on RP2040 due to stability issues " \
		                                     "(https://github.com/juergenpabel/HAL9000/issues/2)");
//TODO		multicore_launch_core1(task_function);
//TODO		result = true;
	}
	return result;
}

#endif

