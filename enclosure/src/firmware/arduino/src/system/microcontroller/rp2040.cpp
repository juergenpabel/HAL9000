#ifdef ARDUINO_ARCH_RP2040

#include <hardware/watchdog.h>
#include <hardware/structs/watchdog.h>
#include <hardware/resets.h>
#include <pico/bootrom.h>
#include <pico/multicore.h>
#include <Wire.h>

#include "system/microcontroller/rp2040.h"
#include "globals.h"


void Microcontroller::start(uint32_t& timestamp) {
	if((watchdog_hw->scratch[5] == 0x00002001) && (watchdog_hw->scratch[6] == 0x00009000)) {
		timestamp = watchdog_hw->scratch[7];
		watchdog_hw->scratch[5] = 0x00000000;
		watchdog_hw->scratch[6] = 0x00000000;
		watchdog_hw->scratch[7] = 0x00000000;
	}
}


void Microcontroller::reset(uint32_t& timestamp) {
	if(timestamp > 0) {
		hw_clear_bits(&watchdog_hw->ctrl, WATCHDOG_CTRL_ENABLE_BITS);
		watchdog_hw->scratch[5] = 0x00002001;
		watchdog_hw->scratch[6] = 0x00009000;
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
			recursive_mutex_init(&this->mutex_map[name]);
			result = true;
		}
	}
	return result;
}


bool Microcontroller::mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		result = recursive_mutex_try_enter(&this->mutex_map[name], nullptr);
	}
	return result;
}


bool Microcontroller::mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		recursive_mutex_enter_blocking(&this->mutex_map[name]);
		result = true;
	}
	return result;
}


bool Microcontroller::mutex_exit(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		recursive_mutex_exit(&this->mutex_map[name]);
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


static TwoWire twowire(i2c0, TWOWIRE_PIN_SDA, TWOWIRE_PIN_SCL);

TwoWire* Microcontroller::twowire_get(uint8_t instance) {
	TwoWire* result = nullptr;
	int      pin_sda = TWOWIRE_PIN_SDA;
	int      pin_scl = TWOWIRE_PIN_SCL;

	if(instance > 0) {
		return nullptr;
	}
	result = &twowire;
	if(g_system_settings.count("device/mcp23X17:i2c/pin-sda") == 1) {
		pin_sda = atoi(g_system_settings["device/mcp23X17:i2c/pin-sda"].c_str());
	}
	if(g_system_settings.count("device/mcp23X17:i2c/pin-scl") == 1) {
		pin_scl = atoi(g_system_settings["device/mcp23X17:i2c/pin-scl"].c_str());
	}
	result->setSDA(pin_sda);
	result->setSCL(pin_scl);
	return result;
}


bool Microcontroller::thread_create(void (*function)(), uint8_t core) {
	bool result = false;

	if(core == 1) {
		multicore_launch_core1(function);
		result = true;
	}
	return result;
}


#endif

