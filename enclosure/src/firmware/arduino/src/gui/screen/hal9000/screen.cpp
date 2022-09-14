#include <etl/string.h>
#include <etl/to_string.h>
#include <etl/format_spec.h>
#include <TimeLib.h>
#include <LittleFS.h>
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
		static StaticJsonDocument<1024> queue;

		queue.clear();
		frame_next = 0;
		deserializeJson(queue, g_system_runtime["gui/screen:hal9000/queue"].c_str());
		if(queue.is<JsonArray>() == false || queue.size() == 0) {
			g_system_runtime["gui/screen:hal9000/queue"] = "[]";
			if(frame_loop == false) {
				g_util_webserial.send("syslog", "gui_screen_hal9000() => empty queue and loop=false, switching to screen 'idle'");
				frame_next = GUI_SEQUENCE_FRAMES_MAX;
				gui_screen_set(gui_screen_idle);
				return;
			}
		}
		if(queue.is<JsonArray>() == true) {
			if(queue.size() > 0) {
				if(queue[0].containsKey("name") && queue[0].containsKey("loop")) {
					sequence_load(queue[0]["name"]);
					frame_loop = queue[0]["loop"].as<std::string>().compare("true") == 0;
				}
				queue.remove(0);
			}
			RuntimeWriter runtimewriter(g_system_runtime, "gui/screen:hal9000/queue");
			serializeJson(queue, runtimewriter);
		}
	}
	if(g_frames[frame_next].size > 0) {
		gui_screen_hal9000_frame_draw(g_frames[frame_next].data, g_frames[frame_next].size);
	}
	frame_next++;
}


static void sequence_load(const char* name) {
	etl::string<GLOBAL_FILENAME_SIZE>  directory;
	etl::string<GLOBAL_FILENAME_SIZE>  filename;
	File                               file = {0};

	for(int i=0; i<GUI_SEQUENCE_FRAMES_MAX; i++) {
		g_frames[i].size = 0;
	}
	directory = "/images/sequences/";
	directory += name;
	directory += "/";
	for(int i=0; i<GUI_SEQUENCE_FRAMES_MAX; i++) {
		filename = directory;
		etl::to_string(i, filename, etl::format_spec().width(2).fill('0'), true);
		filename += ".jpg";
		file = LittleFS.open(filename.c_str(), "r");
		if(file) {
			g_frames[i].size = file.size();
			if(g_frames[i].size > sizeof(jpg_t::data)) {
				g_frames[i].size = 0;
				g_util_webserial.send("syslog", etl::string<UTIL_WEBSERIAL_BODY_SIZE>("JPEG file '").append(filename).append("' too big, skipping"));
			}
			file.read(g_frames[i].data, g_frames[i].size);
			file.close();
		}
	}
	g_util_webserial.send("syslog", etl::string<UTIL_WEBSERIAL_BODY_SIZE>("Frames '").append(name).append("' loaded from littlefs:").append(directory));
}

