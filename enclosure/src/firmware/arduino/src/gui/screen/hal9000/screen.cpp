#include <string>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/hal9000/frame.h"
#include "globals.h"

static void sequence_load(const char* name);


typedef struct {
	uint16_t size;
	uint8_t  data[GUI_SEQUENCE_FRAME_MAXSIZE-sizeof(uint16_t)];
} jpg_t;

static jpg_t g_frames[GUI_SEQUENCE_FRAMES_MAX] = {0};


void gui_screen_hal9000(bool refresh) {
	static uint8_t frame_next = GUI_SEQUENCE_FRAMES_MAX;
	static bool    frame_loop = false;

	if(frame_next == GUI_SEQUENCE_FRAMES_MAX) {
		JSONVar queue;

		frame_next = 0;
		queue = JSONVar::parse(g_system_runtime["gui/screen:hal9000/queue"].c_str());
		if(JSON.typeof(queue) != arduino::String("array") || queue.length() == 0) {
			g_system_runtime["gui/screen:hal9000/queue"] = std::string("[]");
			if(frame_loop == false) {
				g_util_webserial.send("syslog", "gui_screen_hal9000() => empty queue and loop=false, switching to screen 'idle'");
				frame_next = GUI_SEQUENCE_FRAMES_MAX;
				gui_screen_set(gui_screen_idle);
				return;
			}
		}
		if(JSON.typeof(queue) == arduino::String("array")) {
			if(queue.length() > 0) {
				JSONVar queue_new = JSONVar::parse("[]");

				if(queue[0].hasOwnProperty("name") && queue[0].hasOwnProperty("loop")) {
					sequence_load(queue[0]["name"]);
					frame_loop = arduino::String("true").equalsIgnoreCase((const char*)queue[0]["loop"]);
				}
				for(int i=1; i<queue.length(); i++) {
					queue_new[i-1] = queue[i];
				}
				queue = queue_new;
			}
			g_system_runtime["gui/screen:hal9000/queue"] = JSONVar::stringify(queue).c_str();
		}
	}
	if(g_frames[frame_next].size > 0) {
		gui_screen_hal9000_frame_draw(g_frames[frame_next].data, g_frames[frame_next].size);
	}
	frame_next++;
}


static void sequence_load(const char* name) {
	char     directory[256] = {0};
	char     filename[256] = {0};
	File     file = {0};

	for(int i=0; i<GUI_SEQUENCE_FRAMES_MAX; i++) {
		g_frames[i].size = 0;
	}
	snprintf(directory, sizeof(directory), "/images/sequences/%s", name);
	for(int i=0; i<GUI_SEQUENCE_FRAMES_MAX; i++) {
		snprintf(filename, sizeof(filename), "%s/%02d.jpg", directory, i);
		file = LittleFS.open(filename, "r");
		if(file) {
			g_frames[i].size = file.size();
			if(g_frames[i].size > sizeof(jpg_t::data)) {
				g_frames[i].size = 0;
				g_util_webserial.send("syslog", arduino::String("JPEG file '") + filename + arduino::String("' too big, skipping"));
			}
			file.read(g_frames[i].data, g_frames[i].size);
			file.close();
		}
	}
	g_util_webserial.send("syslog", arduino::String("Frames '") + name + "' loaded from littlefs:" + directory);
}

