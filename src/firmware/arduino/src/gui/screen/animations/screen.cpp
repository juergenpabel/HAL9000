#include <FS.h>
#include <LittleFS.h>
#include <etl/list.h>
#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
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
			gui_screen_set(gui_screen_idle);
			g_util_webserial.send("gui:event", "{\"screen\":\"idle\"}", false);
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
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> configJSON;
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> folderJSON;
	       JsonArray                                folders;
	       File file;

	if(LittleFS.exists(filename.c_str()) == false) {
		g_application.notifyError("error", "005", "Animation file: not found", 15);
		return;
	}
	file = LittleFS.open(filename.c_str(), "r");
	if(deserializeJson(configJSON, file) != DeserializationError::Ok) {
		g_application.notifyError("error", "006", "Animation file: JSON error", 15);
		file.close();
		return;
	}
	file.close();
	folders = configJSON.as<JsonArray>();
	for(JsonVariant folder : folders) {
		static etl::string<GLOBAL_FILENAME_SIZE> filename2;
		static animation_t animation;

		animation.directory = "/images/animations/";
		animation.directory += folder.as<const char*>();
		filename2 = animation.directory;
		filename2 += "/animation.json";
		if(LittleFS.exists(filename2.c_str()) == true) {
			file = LittleFS.open(filename2.c_str(), "r");
			if(deserializeJson(folderJSON, file) == DeserializationError::Ok) {
				animation.frames = folderJSON["frames"].as<int>();
				animation.delay  = folderJSON["delay"].as<int>();
				g_animation.push_back(animation);
			}
			file.close();
		}
	}
	g_current_frame = 0;
}


void gui_screen_animation_startup(bool refresh) {
	if(g_gui_buffer == nullptr) {
		if(refresh == true) {
			g_gui.fillScreen(TFT_BLACK);
			g_gui.setTextColor(TFT_RED, TFT_BLACK, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(2);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.drawString("Startup...", TFT_WIDTH/2, TFT_HEIGHT/2);
			delay(30000); //TODO
			gui_screen_set(gui_screen_idle);
			g_util_webserial.send("gui:event", "{\"screen\":\"idle\"}", false);
		}
		return;
	}
	if(g_animation.empty() == true) {
		gui_screen_animation_load("/images/animations/startup.json");
	}
	gui_screen_animations(refresh);
}


void gui_screen_animation_shutdown(bool refresh) {
	if(g_gui_buffer == nullptr) {
		if(refresh == true) {
			g_gui.fillScreen(TFT_BLACK);
			g_gui.setTextColor(TFT_RED, TFT_BLACK, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(2);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.drawString("Shutdown...", TFT_WIDTH/2, TFT_HEIGHT/2);
			delay(5000);
			gui_screen_set(gui_screen_none);
			g_util_webserial.send("gui:event", "{\"screen\":\"none\"}", false);
		}
		return;
	}
	if(g_animation.empty() == true) {
		gui_screen_animation_load("/images/animations/shutdown.json");
	}
	gui_screen_animations(refresh);
}

