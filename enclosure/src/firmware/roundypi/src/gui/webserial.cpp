#include "globals.h"

#include <string.h>
#include <TimeLib.h>
#include <SimpleWebSerial.h>
#include "gui.h"
#include "sequence.h"
#include "splash.h"
#include "frame.h"
#include "jpeg.h"
#include "png.h"


void on_gui_sequence(JSONVar parameter) {
//	if(strncmp("set", (const char*)parameter["action"], 4) == 0) {
//		g_current_sequence->timeout = now() + (long)parameter["timeout"];
//	}
//	if(strncmp("add", (const char*)parameter["action"], 4) == 0) {
//		g_current_sequence->timeout += (long)parameter["timeout"];
//	}

	//if(strncmp("set", (const char*)parameter["action"], 4) == 0) {
	//}
	if(1) { //if(strncmp("add", (const char*)parameter["action"], 4) == 0) {
		if(parameter.hasOwnProperty("sequence")) {
			sequence_add(parameter["sequence"]);
			gui_update(gui_update_sequence);
		}
	}
}


void on_gui_splash(JSONVar parameter) {
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
		g_previous_gui = gui_update(gui_update_splash);
	}
}

