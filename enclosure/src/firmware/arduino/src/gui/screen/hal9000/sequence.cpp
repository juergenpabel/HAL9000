#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/hal9000/frame.h"
#include "gui/screen/hal9000/sequence.h"
#include "globals.h"


typedef struct sequence sequence_t;
typedef struct sequence {
	char        name[32];
	uint32_t    timeout;
	sequence_t* next;
} sequence_t;


void  add_sequence_recursively(JSONVar data, uint8_t offset);

sequence_t      g_sequences_queue[GUI_SEQUENCES_MAX] = {0};
sequence_t*     g_current_sequence = &g_sequences_queue[0];

void screen_sequence(bool refresh) {
/*
	for(int i=0; i<GUI_SEQUENCE_FRAMES_MAX; i++) {
		if(g_frames_jpg[i].size > 0) {
			frame_jpg_draw(g_frames_jpg[i].data, g_frames_jpg[i].size);
		}
	}
	if(g_current_sequence->timeout == 0 || now() > g_current_sequence->timeout) {
		g_current_sequence->name[0] = '\0';
		g_current_sequence = g_current_sequence->next;
		if(g_current_sequence->name[0] != '\0') {
			gui_screen_hal9000_frames_load(g_current_sequence->name);
			if(g_current_sequence->timeout > 0) {
				g_current_sequence->timeout += now();
			}
		} else {
			g_util_webserial.send("syslog", "Sequences queue empty, activating idle handler");
			screen_set(screen_idle);
		}
	}
*/
}

void sequence_add(JSONVar sequence) {
	if(sequence.length() > 0) {
		add_sequence_recursively(sequence, 0);
		gui_screen_hal9000_frames_load(g_current_sequence->name);
	}
}


void add_sequence_recursively(JSONVar data, uint8_t offset) {
	uint8_t     target_offset = 0;
	sequence_t* target_sequence = NULL;

	while(target_offset<GUI_SEQUENCES_MAX && g_sequences_queue[target_offset].name[0]!='\0') {
		target_offset++;
	}
	if(target_offset>=GUI_SEQUENCES_MAX) {
		g_util_webserial.send("syslog", "Sequences queue already full");
		return;
	}
	target_sequence = g_current_sequence;
	if(offset == 0) {
		for(int i=0; i<GUI_SEQUENCES_MAX; i++) {
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
	g_util_webserial.send("syslog", String("Added sequence '") + (const char*)data[offset]["name"] + "' at pos=" + target_offset + " with timeout=" + (long)data[offset]["timeout"]);
	if(offset+1 < data.length()) {
		add_sequence_recursively(data, offset+1);
	}
}

