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
                :AbstractMicrocontroller("esp32")
                ,mutex_map()
                ,twowire_init{false,false}
                ,twowire_data{0,1} {
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
			g_application.setCondition(Microcontroller::reset_condition);
		}
	}
	Microcontroller::original_vprintf = esp_log_set_vprintf(Microcontroller::vprintf);
}


bool Microcontroller::configure(const JsonVariant& configuration) {
	uint8_t pin_sda;
	uint8_t pin_scl;

	if(configuration.containsKey("i2c") == true) {
		if(configuration["i2c"].containsKey("i2c-0") == true) {
			pin_sda = configuration["i2c"]["i2c-0"]["pin-sda"].as<unsigned char>();
			pin_scl = configuration["i2c"]["i2c-0"]["pin-scl"].as<unsigned char>();
			this->twowire_data[0].setPins(pin_sda, pin_scl);
			this->twowire_init[0] = true;
		}
		if(configuration["i2c"].containsKey("i2c-1") == true) {
			pin_sda = configuration["i2c"]["i2c-1"]["pin-sda"].as<unsigned char>();
			pin_scl = configuration["i2c"]["i2c-1"]["pin-scl"].as<unsigned char>();
			this->twowire_data[1].setPins(pin_sda, pin_scl);
			this->twowire_init[1] = true;
		}
	}
	return true;
}


void Microcontroller::reset(uint32_t timestamp, bool rebooting) {
	for(uint8_t i=0; i<2; i++) {
		if(this->twowire_init[i] == true) {
			this->twowire_data[i].end();
		}
	}
	Microcontroller::reset_booting   = rebooting;
	Microcontroller::reset_condition = g_application.getCondition();
	Microcontroller::reset_timestamp = timestamp;
	esp_restart();
}


void Microcontroller::halt() {
	esp_deep_sleep_start();
	//this code should never be executed
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


TwoWire* Microcontroller::twowire_get(uint8_t instance) {
	if(instance >= 2 || this->twowire_init[instance] == false) {
		return nullptr;
	}
	return &this->twowire_data[instance];
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


void Microcontroller::webserial_execute(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
}


#endif

