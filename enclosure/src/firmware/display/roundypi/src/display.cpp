#include "defines.h"
#include "types.h"
#include "globals.h"

#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
//include <SdFat.h>
#include <SimpleWebSerial.h>
#include "display.h"
#include "frame.h"
#include "jpeg.h"

static png_t g_frames_png[FRAMES_PNG_MAX] = {0};
static void  add_sequence_recursively(JSONVar data, uint8_t offset);


sequence_t*     g_current_sequence = &g_sequences_queue[0];
sequence_t      g_sequences_queue[SEQUENCES_MAX] = {0};


void on_display_backlight(JSONVar parameter) {
	if(strncmp("set", (const char*)parameter["action"], 4) == 0) {
		digitalWrite(TFT_BL, (bool)parameter["state"] ? LOW : HIGH);
	}
}


void on_display_sequence(JSONVar parameter) {
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
			JSONVar sequence;

			sequence = parameter["sequence"];
			if(sequence.length() > 0) {
				add_sequence_recursively(sequence, 0);
				display_frames_load(g_current_sequence->name);
				if(g_current_sequence->timeout > 0) {
					g_current_sequence->timeout += now();
				}
			}
		}
	}
}


static void add_sequence_recursively(JSONVar data, uint8_t offset) {
	uint8_t     target_offset = 0;
	sequence_t* target_sequence = NULL;

	while(target_offset<SEQUENCES_MAX && g_sequences_queue[target_offset].name[0]!='\0') {
		target_offset++;
	}
	if(target_offset>=SEQUENCES_MAX) {
		g_webserial.send("RoundyPI", "Sequences queue already full");
		return;
	}
	target_sequence = g_current_sequence;
	while(target_sequence->next != target_sequence) {
		target_sequence = target_sequence->next;
	}
	target_sequence->next = &g_sequences_queue[target_offset];
	target_sequence = target_sequence->next;
	strncpy(target_sequence->name, data[offset]["name"], sizeof(target_sequence->name)-1);
	target_sequence->timeout = (long)data[offset]["timeout"];
	target_sequence->next = target_sequence;

	g_webserial.send("RoundyPI", String("Added sequence '") + (const char*)data[offset]["name"] + "' at pos=" + target_offset + " with timeout=" + (long)data[offset]["timeout"]);
	if(offset+1 < data.length()) {
		add_sequence_recursively(data, offset+1);
	}
}


void on_display_splash(JSONVar parameter) {
	char     filename[256] = {0};
	char*    extension = NULL;

	snprintf(filename, sizeof(filename)-1, "/images/splash/%s", (const char*)parameter["filename"]);
	extension = strrchr(filename, '.');
	if(extension != NULL && strncmp(extension, ".jpg", 5) == 0) {
		splash_jpeg(filename);
	}
}


void display_frames_load(const char* name) {
	char     directory[256] = {0};
	char     filename[256] = {0};
	File     file = {0};

	for(int i=0; i<FRAMES_PNG_MAX; i++) {
		g_frames_png[i].size = 0;
	}
	snprintf(directory, sizeof(directory)-1, "/images/sequences/%s", name);
	for(int i=0; i<FRAMES_PNG_MAX; i++) {
		snprintf(filename, sizeof(filename)-1, "%s/%.2d.png", directory, i);
		file = LittleFS.open(filename, "r");
		if(file) {
			g_frames_png[i].size = file.size();
			file.read(g_frames_png[i].data, g_frames_png[i].size);
			file.close();
		}
	}
	g_webserial.send("RoundyPI", String("Sequence '") + name + "' loaded from littlefs:" + directory);
}


void display_show() {
	static time_t clock_previously = 0;

	if(g_current_sequence->name[0] != '\0') {
		clock_previously = 0;
		for(int i=0; i<FRAMES_PNG_MAX; i++) {
			if(g_frames_png[i].size > 0) {
				frame_png_draw(g_frames_png[i].data, g_frames_png[i].size);
			}
		}
	} else {
		time_t clock_currently = now();

		if(year(clock_currently) >= 2001) {
			if(clock_previously == 0) {
				g_webserial.send("RoundyPI", "Showing clock while idle");
			}
			if(hour(clock_currently) != hour(clock_previously) || minute(clock_currently) != minute(clock_previously)) {
				char clock[6] = {0};

				clock_previously = clock_currently;
				snprintf(clock, sizeof(clock), "%02d:%02d", hour(clock_currently), minute(clock_currently));
				g_tft.drawString(clock, 120, 120);
			}
		}
	}
}

