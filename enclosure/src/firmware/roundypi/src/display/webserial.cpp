#include "globals.h"

#include <string.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>


void on_display_backlight(JSONVar parameter) {
	if(strncmp("set", (const char*)parameter["action"], 4) == 0) {
		digitalWrite(TFT_BL, (bool)parameter["state"] ? LOW : HIGH);
	}
}

