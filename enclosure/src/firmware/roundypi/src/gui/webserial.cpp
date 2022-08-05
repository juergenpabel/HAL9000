#include "globals.h"

#include <string.h>
#include <TimeLib.h>
#include <SimpleWebSerial.h>
#include "screen.h"
#include "sequence.h"
#include "splash.h"
#include "frame.h"
#include "jpeg.h"
#include "png.h"


void on_screen_sequence(JSONVar parameter) {
	if(parameter.hasOwnProperty("sequence")) {
		sequence_add(parameter["sequence"]);
		screen_update(screen_update_sequence, false);
	}
}


void on_screen_splash(JSONVar parameter) {
	char     filename[256] = {0};
	char*    extension = NULL;

	if(parameter.hasOwnProperty("filename")) {
		g_splash_timeout = 0;
		if(parameter.hasOwnProperty("timeout")) {
			g_splash_timeout = (long)parameter["timeout"] + now();
		}
		snprintf(filename, sizeof(filename)-1, "/images/splash/%s", (const char*)parameter["filename"]);
		extension = strrchr(filename, '.');
		if(extension != NULL && strncmp(extension, ".jpg", 5) == 0) {
			splash_jpeg(filename);
		}
		if(extension != NULL && strncmp(extension, ".png", 5) == 0) {
			splash_png(filename);
		}
		g_previous_screen = screen_update(screen_update_splash, false);
	}
}

