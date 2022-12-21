#ifdef ARDUINO_ARCH_ESP32

#include <esp_system.h>
#include <esp_sleep.h>
#include <esp_log.h>

#include <Arduino.h>
#include <Wire.h>

#include "device/microcontroller/esp32.h"
#include "globals.h"


RTC_NOINIT_ATTR bool           Microcontroller::reset_booting;
RTC_NOINIT_ATTR Condition      Microcontroller::reset_condition;
RTC_NOINIT_ATTR uint32_t       Microcontroller::reset_timestamp;
                vprintf_like_t Microcontroller::original_vprintf;


Microcontroller::Microcontroller()
                :AbstractMicrocontroller() {
}


void Microcontroller::start(uint32_t& timestamp, bool& host_booting) {
	if(esp_reset_reason() == ESP_RST_POWERON) {
		host_booting = true;
		timestamp = 0;
	} else {
		host_booting = Microcontroller::reset_booting;
		if(Microcontroller::reset_timestamp > 1009843199 /*2001-12-31 23:59:59*/) {
			timestamp = Microcontroller::reset_timestamp;
		}
		if(Microcontroller::reset_condition != ConditionUnknown) {
			g_system_runtime.setCondition(Microcontroller::reset_condition);
		}
	}
	Microcontroller::original_vprintf = esp_log_set_vprintf(Microcontroller::vprintf);
}


void Microcontroller::reset(uint32_t timestamp, bool rebooting) {
	this->twowire_get(0, TWOWIRE_PIN_SDA, TWOWIRE_PIN_SCL)->end();
	Microcontroller::reset_booting = rebooting;
	Microcontroller::reset_condition = g_system_runtime.getCondition();
	Microcontroller::reset_timestamp = timestamp;
	esp_restart();
}


void Microcontroller::halt() {
	esp_deep_sleep_start();
	//this code should never be taken
	while(true) {
		delay(1000);
	}
}


bool Microcontroller::mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name, bool recursive) {
	bool              result = false;

	if(this->mutex_map.count(name) == 0) {
		if(this->mutex_map.size() < this->mutex_map.capacity()) {
			Semaphore& semaphore = this->mutex_map[name];

			if(recursive == true) {
				semaphore.handle = xSemaphoreCreateRecursiveMutexStatic(&semaphore.data);
			} else {
				semaphore.handle = xSemaphoreCreateMutexStatic(&semaphore.data);
			}
			semaphore.recursive = recursive;
			result = true;
		}
	}
	return result;
}


bool Microcontroller::mutex_try_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		Semaphore& semaphore = this->mutex_map[name];

		if(semaphore.recursive == true) {
			if(xSemaphoreTakeRecursive(semaphore.handle, (TickType_t)10) == pdTRUE) {
				result = true;
			}
		}
		if(semaphore.recursive == false) {
			if(xSemaphoreTake(semaphore.handle, (TickType_t)10) == pdTRUE) {
				result = true;
			}
		}
	}
	return result;
}


bool Microcontroller::mutex_enter(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		Semaphore& semaphore = this->mutex_map[name];

		while(result != true) {
			if(semaphore.recursive == true) {
				if(xSemaphoreTakeRecursive(semaphore.handle, (TickType_t)0) == pdTRUE) {
					result = true;
				}
			}
			if(semaphore.recursive == false) {
				if(xSemaphoreTake(semaphore.handle, (TickType_t)0) == pdTRUE) {
					result = true;
				}
			}
		}
	}
	return result;
}


bool Microcontroller::mutex_exit(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool result = false;

	if(this->mutex_map.count(name) == 1) {
		Semaphore& semaphore = this->mutex_map[name];

		if(semaphore.recursive == true) {
			xSemaphoreGiveRecursive(semaphore.handle);
		} else {
			xSemaphoreGive(semaphore.handle);
		}
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
	static bool    twowire_init = false;

	if(twowire_init == false) {
		twowire.setPins(pin_sda, pin_scl);
		twowire_init = true;
	}
	return &twowire;
}


static void thread_function(void* parameter) {
	void (*function)() = (void (*)())parameter;

	function();
}


bool Microcontroller::thread_create(void (*function)(), uint8_t core) {
        static bool result = false;

	if(result == true) {
//TODO: error handling
		return false;
	}
	if(core == 1) {
		xTaskCreatePinnedToCore(thread_function, "MCP23X17", 4096, (void*)function, configMAX_PRIORITIES - 1, nullptr, 1);
		result = true;
	}
	return result;
}


int Microcontroller::vprintf(const char* format, va_list message) {
	const char* webserial_format = "[\"syslog/error\", \"%s\"]";

	if(strncmp(format, "%s", 3) == 0) {
		format = webserial_format;
	}
	return Microcontroller::original_vprintf(format, message);
}


#endif

