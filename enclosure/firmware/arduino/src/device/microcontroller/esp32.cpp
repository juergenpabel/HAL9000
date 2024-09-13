#ifdef ARDUINO_ARCH_ESP32

#include <esp_system.h>
#include <esp_sleep.h>
#include <esp_log.h>

#include <Arduino.h>
#include <Wire.h>

#include "device/microcontroller/esp32.h"
#include "globals.h"


RTC_NOINIT_ATTR uint32_t       Microcontroller::reset_timestamp;
                vprintf_like_t Microcontroller::original_vprintf;


Microcontroller::Microcontroller()
                :AbstractMicrocontroller("esp32")
                ,mutex_map()
                ,twowire_init{false,false}
                ,twowire_data{0,1} {
}


void Microcontroller::start(uint32_t& timestamp) {
	if(esp_reset_reason() == ESP_RST_POWERON) {
		timestamp = 0;
	} else {
		if(Microcontroller::reset_timestamp > 1009843199 /*2001-12-31 23:59:59*/) {
			timestamp = Microcontroller::reset_timestamp;
		}
	}
	Microcontroller::original_vprintf = esp_log_set_vprintf(Microcontroller::vprintf);
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
				this->twowire_data[0].setPins(pin_sda, pin_scl);
				this->twowire_init[0] = true;
			} else {
				error_details = "board configuration for 'i2c-0' is missing 'pin-sda' and/or 'pin-scl' options";
			}
		}
		if(configuration["i2c"].containsKey("i2c-1") == true) {
			if(configuration["i2c"]["i2c-1"].containsKey("pin-sda") == true && configuration["i2c"]["i2c-1"].containsKey("pin-scl") == true) {
				pin_sda = configuration["i2c"]["i2c-1"]["pin-sda"].as<unsigned char>();
				pin_scl = configuration["i2c"]["i2c-1"]["pin-scl"].as<unsigned char>();
				this->twowire_data[1].setPins(pin_sda, pin_scl);
				this->twowire_init[1] = true;
			} else {
				error_details = "board configuration for 'i2c-1' is missing 'pin-sda' and/or 'pin-scl' options";
			}
		}
	}
	if(error_details.empty() == false) {
		g_application.notifyError("critical", "213", "Board error", error_details);
		return false;
	}
	return true;
}


void Microcontroller::reset(uint32_t timestamp) {
	for(uint8_t i=0; i<2; i++) {
		if(this->twowire_init[i] == true) {
			this->twowire_data[i].end();
		}
	}
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


bool Microcontroller::mutex_create(const etl::string<GLOBAL_KEY_SIZE>& name) {
	bool              result = false;

	if(this->mutex_map.count(name) == 0) {
		if(this->mutex_map.size() < this->mutex_map.capacity()) {
			Semaphore& semaphore = this->mutex_map[name];

			semaphore.handle = xSemaphoreCreateMutexStatic(&semaphore.data);
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

		while(result != true) {
			if(xSemaphoreTake(semaphore.handle, (TickType_t)0) == pdTRUE) {
				result = true;
			}
		}
	}
	return result;
}


bool Microcontroller::mutex_leave(const etl::string<GLOBAL_KEY_SIZE>& name) {
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


TwoWire* Microcontroller::twowire_get(uint8_t instance) {
	if(instance >= 2 || this->twowire_init[instance] == false) {
		return nullptr;
	}
	return &this->twowire_data[instance];
}


static void task_start(void* parameter) {
	void (*task_function)() = (void (*)())parameter;

	task_function();
}


bool Microcontroller::task_create(const etl::string<GLOBAL_KEY_SIZE>& task_name, void (*task_function)(), uint8_t core) {
	if(core != 0 && core != 1) {
		g_util_webserial.send("syslog/error", "ESP32: invalid core in Microcontroller::task_create()");
		return false;
	}
	xTaskCreatePinnedToCore(task_start, task_name.c_str(), 8192, (void*)task_function, configMAX_PRIORITIES/2, nullptr, 1-core);
	return true;
}


int Microcontroller::vprintf(const char* format, va_list message) {
	const char* webserial_format = "[\"syslog/error\", \"%s\"]";

	if(strncmp(format, "%s", 3) == 0) {
		format = webserial_format;
	}
	return Microcontroller::original_vprintf(format, message);
}

#endif

