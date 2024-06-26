#include <FS.h>
#include <LittleFS.h>
#include <TimeLib.h>
#include <etl/string.h>
#include <etl/to_string.h>
#include <etl/format_spec.h>

#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/hal9000/screen.h"
#include "gui/screen/hal9000/frame.h"
#include "application/environment.h"
#include "globals.h"

static void sequence_load(const char* name);


typedef struct {
	uint16_t size;
	uint8_t  data[GUI_SCREEN_HAL9000_SEQUENCE_FRAME_MAXSIZE-sizeof(uint16_t)];
} jpeg_t;

static jpeg_t g_sequence_frames[GUI_SCREEN_HAL9000_SEQUENCE_FRAMES_MAX] = {0};


void gui_screen_hal9000(bool refresh) {
	static uint8_t frame_next = GUI_SCREEN_HAL9000_SEQUENCE_FRAMES_MAX;
	static bool    frame_loop = false;

	if(g_gui_buffer == nullptr) {
		if(refresh == true) {
			g_gui.fillScreen(TFT_BLACK);
			g_gui.fillCircle(TFT_WIDTH/2, TFT_HEIGHT/2, min(GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT)/10, TFT_RED);
		}
		return;
	}
	if(frame_next == GUI_SCREEN_HAL9000_SEQUENCE_FRAMES_MAX) {
		static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> queue;

		frame_next = 0;
		g_sequence_frames[frame_next].size = 0;
		queue.clear();
		deserializeJson(queue, g_application.getEnv("gui/screen:hal9000/queue").c_str());
		if(queue.is<JsonArray>() == false || queue.as<JsonArray>().size() == 0) {
			g_application.setEnv("gui/screen:hal9000/queue", "[]");
			if(frame_loop == false) {
				g_util_webserial.send("syslog/debug", "gui_screen_hal9000() => empty queue and loop=false, switching to screen 'idle'");
				frame_next = GUI_SCREEN_HAL9000_SEQUENCE_FRAMES_MAX;
				gui_screen_set(gui_screen_idle);
				g_util_webserial.send("gui/event", "{\"screen\":\"idle\"}", false);
				return;
			}
		}
		if(queue.is<JsonArray>() == true) {
			if(queue.size() > 0) {
				frame_loop = false;
				if(queue[0].containsKey("name") && queue[0].containsKey("loop")) {
					sequence_load(queue[0]["name"]);
					if(strncasecmp(queue[0]["loop"].as<const char*>(), "true", 5) == 0) {
						frame_loop = true;
					}
				}
				queue.remove(0);
			}
			EnvironmentWriter environmentwriter(g_application, "gui/screen:hal9000/queue");
			serializeJson(queue, environmentwriter);
		}
	}
	if(g_sequence_frames[frame_next].size > 0) {
		gui_screen_hal9000_frame_draw(g_sequence_frames[frame_next].data, g_sequence_frames[frame_next].size);
	}
	frame_next++;
}


static void sequence_load(const char* name) {
	etl::string<GLOBAL_FILENAME_SIZE>  directory("/images/sequences/");
	etl::string<GLOBAL_FILENAME_SIZE>  filename;
	File                               file = {0};

	for(int i=0; i<GUI_SCREEN_HAL9000_SEQUENCE_FRAMES_MAX; i++) {
		g_sequence_frames[i].size = 0;
	}
	directory += name;
	directory += "/";
	for(int i=0; i<GUI_SCREEN_HAL9000_SEQUENCE_FRAMES_MAX; i++) {
		filename = directory;
		etl::to_string(i, filename, etl::format_spec().width(2).fill('0'), true);
		filename += ".jpg";
		file = LittleFS.open(filename.c_str(), "r");
		if(file) {
			g_sequence_frames[i].size = file.size();
			if(g_sequence_frames[i].size > sizeof(jpeg_t::data)) {
				g_sequence_frames[i].size = 0;
				g_util_webserial.send("syslog/warn", etl::string<GLOBAL_VALUE_SIZE>("JPEG file '").append(filename).append("' too big, skipping"));
			}
			file.read(g_sequence_frames[i].data, g_sequence_frames[i].size);
			file.close();
		}
	}
	g_util_webserial.send("syslog/debug", etl::string<GLOBAL_VALUE_SIZE>("Frames '").append(name).append("' loaded from littlefs:").append(directory));
}

