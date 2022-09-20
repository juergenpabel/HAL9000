#ifndef __ROUNDYPI_SDCARD_H__
#define __ROUNDYPI_SDCARD_H__

#include <etl/string.h>
#include <ArduinoJson.h>


class SDCard {
	protected:
		uint8_t  pin_cs;
		bool     ready;
	public:
		SDCard();
		void init();

		void list(const etl::string<GLOBAL_FILENAME_SIZE>& directory, JsonArray& result);
		void read(const etl::string<GLOBAL_FILENAME_SIZE>& filename, JsonArray& result);
		void remove(const etl::string<GLOBAL_FILENAME_SIZE>& filename, JsonArray& result);
};

#endif

