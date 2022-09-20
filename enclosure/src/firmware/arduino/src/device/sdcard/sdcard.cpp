#include <SPI.h>
#include <SD.h>
#include <SdFat.h>
#include <etl/string.h>

#include "device/sdcard/sdcard.h"
#include "globals.h"


SDCard::SDCard() {
	this->pin_cs = SDCARD_CS;
	this->ready = false;
}


void SDCard::begin() {
	if(this->ready == false) {
		if(g_system_settings.count("device/sdcard:spi/pin-cs") == 1) {
			this->pin_cs = atoi(g_system_settings["device/sdcard:spi/pin-cs"].c_str());
		}
		if(!SD.begin(this->pin_cs)) {
			g_util_webserial.send("syslog", "SDCard::begin() => SD.begin() failed");
			return;
		}
		this->ready = true;
	}
}


void SDCard::list(const etl::string<GLOBAL_FILENAME_SIZE>& directory, JsonArray& result) {
	if(this->ready == true) {
		File  dir;
		File  entry;

		dir = SD.open(directory.c_str());
		do {
			entry = dir.openNextFile();
			if(entry) {
				JsonObject result_entry;

				result_entry = result.createNestedObject();
				result_entry["name"] = entry.name();
				result_entry["type"] = (char*)entry.isDirectory() ? "dir" : "file";
				result_entry["size"] = (char*)entry.size();
				entry.close();
			}
		} while(entry);
		dir.close();
	}
}


void SDCard::read(const etl::string<GLOBAL_FILENAME_SIZE>& filename, JsonArray& result) {
	if(this->ready == true) {
		File  file;

		file = SD.open(filename.c_str());
		while(file.available()) {
			char  line[128] = {0};
			int   line_pos = 0;

			line_pos = file.readBytesUntil('\n', line, sizeof(line)-1);
			if(line_pos > 0) {
				result.add(line);
			}
		};
		file.close();
	}
}


void SDCard::remove(const etl::string<GLOBAL_FILENAME_SIZE>& filename, JsonArray& result) {
	if(this->ready == true) {
		if(SD.exists(filename.c_str()) == true) {
			SD.remove(filename.c_str());
			result.add(true);
		}
	}
}

