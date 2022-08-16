#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/hal9000/frame.h"
#include "globals.h"


typedef struct {
	uint16_t size;
	uint8_t  data[GUI_SEQUENCE_FRAME_MAXSIZE-sizeof(uint16_t)];
} jpg_t;


static jpg_t g_gui_screen_hal9000_frames[GUI_SEQUENCE_FRAMES_MAX] = {0};


void gui_screen_hal9000(bool refresh) {
	static uint8_t i=0;

	if(i<GUI_SEQUENCE_FRAMES_MAX) {
		if(g_gui_screen_hal9000_frames[i].size > 0) {
			gui_screen_hal9000_frame_draw(g_gui_screen_hal9000_frames[i].data, g_gui_screen_hal9000_frames[i].size);
		}
		i++;
	} else {
		i = 0;
	}
}


void gui_screen_hal9000_frames_load(const char* name) {
	char     directory[256] = {0};
	char     filename[256] = {0};
	File     file = {0};

	for(int i=0; i<GUI_SEQUENCE_FRAMES_MAX; i++) {
		g_gui_screen_hal9000_frames[i].size = 0;
	}
	snprintf(directory, sizeof(directory)-1, "/images/frames/%s", name);
	for(int i=0; i<GUI_SEQUENCE_FRAMES_MAX; i++) {
		snprintf(filename, sizeof(filename)-1, "%s/%.2d.jpg", directory, i);
		file = LittleFS.open(filename, "r");
		if(file) {
			g_gui_screen_hal9000_frames[i].size = file.size();
			file.read(g_gui_screen_hal9000_frames[i].data, g_gui_screen_hal9000_frames[i].size);
			file.close();
		}
	}
	g_util_webserial.send("syslog", String("Frames '") + name + "' loaded from littlefs:" + directory);
}

