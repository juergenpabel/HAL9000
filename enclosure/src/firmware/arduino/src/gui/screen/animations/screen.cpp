#include <etl/list.h>
#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/screen/screen.h"
#include "system/system.h"
#include "util/json.h"
#include "util/jpeg.h"
#include "globals.h"


typedef struct {
	etl::string<GLOBAL_FILENAME_SIZE> directory;
	int                               frames;
	int                               delay;
} animation_t;

static etl::list<animation_t, 8>  g_animation;
static int                        g_current_frame = 0;


static void gui_screen_animations(bool refresh) {
	if(g_current_frame >= g_animation.front().frames) {
		g_animation.pop_front();
		g_current_frame = 0;
		if(g_animation.empty() == true) {
			gui_screen_set(gui_screen_none);
			return;
		}
	}
	if(refresh == true) {
		static etl::string<GLOBAL_FILENAME_SIZE> filename;
		static etl::format_spec                  frame_format(10, 2, 0, false, false, false, false, '0');

		filename = g_animation.front().directory;
		if(filename.back() != '/') {
			filename += "/";
		}
		etl::to_string(g_current_frame, filename, frame_format, true);
		filename += ".jpg";
		util_jpeg_decode565_littlefs(filename.c_str(), g_gui_buffer, GUI_SCREEN_WIDTH*GUI_SCREEN_HEIGHT*sizeof(uint16_t));
		g_gui.pushImage((TFT_WIDTH-GUI_SCREEN_WIDTH)/2, (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2, GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT, (uint16_t*)g_gui_buffer);
		delay(g_animation.front().delay);
		g_current_frame++;
	}
}


static void gui_screen_animation_load(const etl::string<GLOBAL_FILENAME_SIZE>& filename) {
	static JSON configJSON;
	static JSON folderJSON;
	JsonArray   folders;

	if(configJSON.load(filename) == false) {
		//TODO:gui_screen_set(error);
		return;
	}
	folders = configJSON.as<JsonArray>();
	for(JsonVariant folder : folders) {
		static etl::string<GLOBAL_FILENAME_SIZE> filename;
		static animation_t animation;

		animation.directory = "/images/animations/";
		animation.directory += folder.as<const char*>();
		filename = animation.directory;
		filename += "/animation.json";
		if(folderJSON.load(filename) == true) {
			animation.frames = folderJSON.getNumber("frames");
			animation.delay  = folderJSON.getNumber("delay");
			g_animation.push_back(animation);
		}
	}
	g_current_frame = 0;
}


void gui_screen_animation_startup(bool refresh) {
	if(g_animation.empty() == true) {
		gui_screen_animation_load("/images/animations/startup.json");
	}
	gui_screen_animations(refresh);
}


void gui_screen_animation_shutdown(bool refresh) {
	if(g_animation.empty() == true) {
		gui_screen_animation_load("/images/animations/shutdown.json");
	}
	gui_screen_animations(refresh);
}

