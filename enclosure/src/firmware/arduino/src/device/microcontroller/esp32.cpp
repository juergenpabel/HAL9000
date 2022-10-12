#ifdef ARDUINO_ARCH_ESP32

#include <Arduino.h>
#include <Wire.h>

#include "device/microcontroller/esp32.h"


void Microcontroller::start(uint32_t& timestamp, bool& booting) {
}


void Microcontroller::reset(uint32_t timestamp, bool rebooting) {
	ESP.restart();
}


void Microcontroller::halt() {
	while(true) {
		delay(1000);
	}
}


bool Microcontroller::mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool              result = false;

	if(this->mutex_map.count(name) == 0) {
		if(this->mutex_map.size() < this->mutex_map.capacity()) {
			Semaphore& semaphore = this->mutex_map[name];

			semaphore.handle = xSemaphoreCreateCountingStatic(5, 0, &semaphore.data);
			result = true;
		}
	}
	return result;
}


bool Microcontroller::mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		Semaphore& semaphore = this->mutex_map[name];

		if(xSemaphoreTake(semaphore.handle, (TickType_t)10) == pdTRUE) {
			result = true;
		}
	}
	return result;
}


bool Microcontroller::mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		Semaphore& semaphore = this->mutex_map[name];

		while(result == false) {
			if(xSemaphoreTake(semaphore.handle, (TickType_t)0) == pdTRUE) {
				result = true;
			}
		}
	}
	return result;
}


bool Microcontroller::mutex_exit(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		Semaphore& semaphore = this->mutex_map[name];

		xSemaphoreGive(semaphore.handle);
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


TwoWire* Microcontroller::twowire_get(uint8_t instance, uint8_t pin_sda, uint8_t pin_scl) {
	static TwoWire twowire(0);

	twowire.setPins(pin_sda, pin_scl);
	return &twowire;
}


static void thread_function(void* parameter) {
	void (*function)() = (void (*)())parameter;

	function();
}


bool Microcontroller::thread_create(void (*function)(), uint8_t core) {
        bool result = false;

	if(core == 1) {
		xTaskCreatePinnedToCore(thread_function, "MCP23X17", 4096, (void*)function, configMAX_PRIORITIES - 1, nullptr, 1);
		result = true;
	}
	return result;
}


#endif

