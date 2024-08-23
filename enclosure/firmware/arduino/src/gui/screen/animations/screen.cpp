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


static void gui_screen_animations_load(const etl::string<GLOBAL_FILENAME_SIZE>& filename);

typedef struct {
	etl::string<GLOBAL_FILENAME_SIZE> directory;
	etl::string<GLOBAL_VALUE_SIZE>    title;
	int                               frames;
	int                               delay;
	boolean                           loop;
	etl::string<GLOBAL_VALUE_SIZE>    onthis_webserial;
	etl::string<GLOBAL_VALUE_SIZE>    onnext_webserial;
} animation_t;

static etl::list<animation_t, 8>  g_animation;
static int                        g_current_frame = 0;


gui_refresh_t gui_screen_animations(bool refresh) {
	static etl::string<GLOBAL_FILENAME_SIZE> filename;
	static etl::format_spec                  frame_format(10, 2, 0, false, false, false, false, '0');

	if(g_application.hasEnv("gui/screen:animations/name") == true) {
		filename  = "/system/gui/screen/animations/";
		filename += g_application.getEnv("gui/screen:animations/name");
		filename += ".json";
		g_device_microcontroller.mutex_enter("gpio");
		gui_screen_animations_load(filename);
		g_device_microcontroller.mutex_leave("gpio");
		if(g_animation.empty() == true) {
			g_util_webserial.send("syslog/error", "error loading json data for gui/screen 'animations':");
			g_util_webserial.send("syslog/error", filename);
		}
	}
	if(g_animation.empty() == false) {
		animation_t* current_animation = nullptr;

		current_animation = &g_animation.front();
		if(g_current_frame >= current_animation->frames) {
			g_current_frame = 0;
			if(current_animation->loop == true) {
				if(g_application.hasEnv("gui/screen:animations/loop") == true) {
					if(g_application.getEnv("gui/screen:animations/loop") == "false") {
						g_application.delEnv("gui/screen:animations/loop");
						current_animation->loop = false;
					}
				}
			}
			if(current_animation->loop == false) {
				if(current_animation->onnext_webserial.empty() == false) {
					g_util_webserial.handle(current_animation->onnext_webserial);
				}
				g_animation.pop_front();
				if(g_animation.empty() == true) {
					return RefreshIgnore;
				}
				current_animation = &g_animation.front();
			}
		}
		if(g_current_frame == 0) {
			if(current_animation->onthis_webserial.empty() == false) {
				g_util_webserial.handle(current_animation->onthis_webserial);
			}
		}
		if(g_gui_screen.getPointer() != nullptr) {
			filename = current_animation->directory;
			if(filename.back() != '/') {
				filename += "/";
			}
			etl::to_string(g_current_frame, filename, frame_format, true);
			filename += ".jpg";
			util_jpeg_decode565_littlefs(filename.c_str(), (uint16_t*)g_gui_screen.getPointer(), GUI_SCREEN_WIDTH*GUI_SCREEN_HEIGHT*sizeof(uint16_t));
			g_gui_screen.pushSprite((g_gui.width()-GUI_SCREEN_WIDTH)/2, (g_gui.height()-GUI_SCREEN_HEIGHT)/2);
		} else {
			if(g_current_frame == 0) {
				g_device_microcontroller.mutex_enter("gpio");
				g_gui.fillScreen(TFT_BLACK);
				g_gui.setTextColor(TFT_RED, TFT_BLACK, false);
				g_gui.setTextFont(1);
				g_gui.setTextSize(3);
				g_gui.setTextDatum(MC_DATUM);
				g_gui.drawString(current_animation->title.c_str(), g_gui.width()/2, g_gui.height()/2);
				g_device_microcontroller.mutex_leave("gpio");
			}
			delay(50); // roughly estimated image loading-time difference
		}
		delay(current_animation->delay);
		g_current_frame++;
	}
	return RefreshIgnore;
}


static void gui_screen_animations_load(const etl::string<GLOBAL_FILENAME_SIZE>& filename) {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> animationsJSON;
	       File file;

	g_application.delEnv("gui/screen:animations/name");
	g_application.delEnv("gui/screen:animations/loop");
	if(LittleFS.exists(filename.c_str()) == false) {
		g_application.notifyError("error", "13", "Animation error", filename);
		return;
	}
	file = LittleFS.open(filename.c_str(), "r");
	if(deserializeJson(animationsJSON, file) != DeserializationError::Ok) {
		g_application.notifyError("error", "13", "Animation error", filename);
		file.close();
		return;
	}
	file.close();
	for(JsonVariant animationJSON : animationsJSON.as<JsonArray>()) {
		static animation_t animation;

		animation.directory.clear();
		animation.title.clear();
		animation.frames = 0;
		animation.delay = 0;
		animation.loop = false;
		animation.onthis_webserial.clear();
		animation.onnext_webserial.clear();
		if(animationJSON.containsKey("directory") == false) {
			g_application.notifyError("error", "13", "Animation error", filename);
			return;
		}
		animation.directory = animationJSON["directory"].as<const char*>();
		if(animationJSON.containsKey("title") == true) {
			animation.title = animationJSON["title"].as<const char*>();
		}
		if(animationJSON.containsKey("frames") == true) {
			animation.frames = animationJSON["frames"].as<int>();
		}
		if(animationJSON.containsKey("delay") == true) {
			animation.delay = animationJSON["delay"].as<int>();
		}
		if(animationJSON.containsKey("loop") == true) {
			animation.loop = animationJSON["loop"].as<bool>();
		}
		if(animationJSON.containsKey("on:this") == true) {
			if(animationJSON["on:this"].containsKey("webserial") == true) {
				animation.onthis_webserial = animationJSON["on:this"]["webserial"].as<const char*>();
			}
		}
		if(animationJSON.containsKey("on:next") == true) {
			if(animationJSON["on:next"].containsKey("webserial") == true) {
				animation.onnext_webserial = animationJSON["on:next"]["webserial"].as<const char*>();
			}
		}
		g_animation.push_back(animation);
	}
	g_current_frame = 0;
}


gui_refresh_t gui_screen_animations_startup(bool refresh) {
	g_device_microcontroller.mutex_enter("gpio");
	gui_screen_animations_load("/system/gui/screen/animations/startup.json");
	g_device_microcontroller.mutex_leave("gpio");
	gui_screen_set("animations", gui_screen_animations, false);
	return RefreshIgnore;
}


gui_refresh_t gui_screen_animations_shutdown(bool refresh) {
	g_device_microcontroller.mutex_enter("gpio");
	gui_screen_animations_load("/system/gui/screen/animations/shutdown.json");
	g_device_microcontroller.mutex_leave("gpio");
	gui_screen_set("animations", gui_screen_animations, false);
	return RefreshIgnore;
}

