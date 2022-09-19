#ifndef __ROUNDYPI_SDCARD_H__
#define __ROUNDYPI_SDCARD_H__

#include <etl/string.h>
#include <ArduinoJson.h>


class SDCard {
	protected:
//TODO		etl::string<2> PIN_NAMES[16];
	public:
		SDCard();
		void init();

		void format(const etl::string<GLOBAL_FILENAME_SIZE>& filesystem, JsonArray& result);
		void list(const etl::string<GLOBAL_FILENAME_SIZE>& directory, JsonArray& result);
		void read(const etl::string<GLOBAL_FILENAME_SIZE>& filename, JsonArray& result);
		void write(const etl::string<GLOBAL_FILENAME_SIZE>& filename, JsonArray& result);
		void remove(const etl::string<GLOBAL_FILENAME_SIZE>& filename, JsonArray& result);
};

#endif

