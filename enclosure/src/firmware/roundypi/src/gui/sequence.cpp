#include "globals.h"

#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
//include <SdFat.h>
#include <SimpleWebSerial.h>
#include "screen.h"
#include "overlay.h"
#include "frame.h"
#include "jpeg.h"


typedef struct {
	uint16_t size;
	uint8_t  data[4096+512-2];
} png_t;

typedef struct sequence sequence_t;
typedef struct sequence {
	char        name[32];
	uint32_t    timeout;
	sequence_t* next;
} sequence_t;


static png_t g_frames_png[DISPLAY_SEQUENCE_FRAMES_MAX] = {0};
void  add_sequence_recursively(JSONVar data, uint8_t offset);


sequence_t      g_sequences_queue[DISPLAY_SEQUENCES_MAX] = {0};
sequence_t*     g_current_sequence = &g_sequences_queue[0];

void screen_update_sequence(bool refresh) {
	for(int i=0; i<DISPLAY_SEQUENCE_FRAMES_MAX; i++) {
		if(g_frames_png[i].size > 0) {
			frame_png_draw(g_frames_png[i].data, g_frames_png[i].size);
		}
	}
	if(g_current_sequence->timeout == 0 || now() > g_current_sequence->timeout) {
		g_current_sequence->name[0] = '\0';
		g_current_sequence = g_current_sequence->next;
		if(g_current_sequence->name[0] != '\0') {
			screen_frames_load(g_current_sequence->name);
			if(g_current_sequence->timeout > 0) {
				g_current_sequence->timeout += now();
			}
		} else {
			g_webserial.send("RoundyPI", "Sequences queue empty, activating idle handler");
			screen_update(screen_update_idle, false);
		}
	}
}

void sequence_add(JSONVar sequence) {
	if(sequence.length() > 0) {
		add_sequence_recursively(sequence, 0);
		screen_frames_load(g_current_sequence->name);
	}
}


void add_sequence_recursively(JSONVar data, uint8_t offset) {
	uint8_t     target_offset = 0;
	sequence_t* target_sequence = NULL;

	while(target_offset<DISPLAY_SEQUENCES_MAX && g_sequences_queue[target_offset].name[0]!='\0') {
		target_offset++;
	}
	if(target_offset>=DISPLAY_SEQUENCES_MAX) {
		g_webserial.send("RoundyPI", "Sequences queue already full");
		return;
	}
	target_sequence = g_current_sequence;
	if(offset == 0) {
		for(int i=0; i<DISPLAY_SEQUENCES_MAX; i++) {
			if(target_sequence == &g_sequences_queue[i]) {
				target_offset = i;
			}
		}
	}
	if(offset > 0 || g_current_sequence->next != g_current_sequence) {
		while(target_sequence->next != target_sequence) {
			if(target_sequence->next == NULL) {
				target_sequence->next = target_sequence;
			}
			target_sequence = target_sequence->next;
		}
		target_sequence->next = &g_sequences_queue[target_offset];
		target_sequence = target_sequence->next;
	}
	strncpy(target_sequence->name, data[offset]["name"], sizeof(target_sequence->name)-1);
	target_sequence->timeout = (long)data[offset]["timeout"];
	target_sequence->next = target_sequence;
	g_webserial.send("RoundyPI", String("Added sequence '") + (const char*)data[offset]["name"] + "' at pos=" + target_offset + " with timeout=" + (long)data[offset]["timeout"]);
	if(offset+1 < data.length()) {
		add_sequence_recursively(data, offset+1);
	}
}


void screen_frames_load(const char* name) {
	char     directory[256] = {0};
	char     filename[256] = {0};
	File     file = {0};

	for(int i=0; i<DISPLAY_SEQUENCE_FRAMES_MAX; i++) {
		g_frames_png[i].size = 0;
	}
	snprintf(directory, sizeof(directory)-1, "/images/sequences/%s", name);
	for(int i=0; i<DISPLAY_SEQUENCE_FRAMES_MAX; i++) {
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

