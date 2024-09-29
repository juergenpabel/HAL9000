#include <FS.h>
#include <LittleFS.h>
#include <etl/list.h>
#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


typedef struct {
	etl::string<GLOBAL_VALUE_SIZE>    title;
	unsigned long                     duration;
	etl::string<GLOBAL_FILENAME_SIZE> directory;
	unsigned int                      frames;
	boolean                           loop;
	etl::string<GLOBAL_VALUE_SIZE>    onthis_webserial;
	etl::string<GLOBAL_VALUE_SIZE>    onnext_webserial;
} animation_t;

typedef etl::list<animation_t, 8>  animations_t;


static void gui_screen_animations_load(const etl::string<GLOBAL_FILENAME_SIZE>& filename, animations_t& animations);


unsigned long gui_screen_animations(unsigned long validity, TFT_eSPI* gui) {
	static animations_t  animations;
	       animation_t*  animation_current = nullptr;
	static unsigned int  animation_current_frame = 0;

	if(validity == GUI_RELOAD) {
		animations.clear();
		return GUI_INVALIDATED;
	}
	if(g_system_application.hasEnv("gui/screen:animations/name") == true) {
		static etl::string<GLOBAL_FILENAME_SIZE>       filename;
		static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

		switch(animations.empty()) {
			case false:
				if(g_system_application.getEnv("gui/screen:animations/loop").compare("false") != 0) {
					for(animations_t::const_iterator iter=animations.begin(); iter!=animations.end(); ++iter) {
						if(iter->loop == true) {
							g_system_application.setEnv("gui/screen:animations/loop", "false");
						}
					}
				}
				break;
			case true:
				animation_current_frame = 0;
				filename  = "/system/gui/screen/animations/";
				filename += g_system_application.getEnv("gui/screen:animations/name");
				filename += ".json";
				g_system_application.delEnv("gui/screen:animations/name");
				if(gui != &g_gui) {
					g_device_microcontroller.mutex_enter("gpio");
				}
				gui_screen_animations_load(filename, animations);
				if(gui != &g_gui) {
					g_device_microcontroller.mutex_leave("gpio");
				}
				if(animations.empty() == true) {
					g_system_application.addErrorContext("gui_screen_animations(): gui_screen_animations_load() returned " \
					                     "empty set for: 'TODO:filename'");
					return GUI_ERROR;
				}
				if(g_system_application.hasEnv("gui/screen:animations/loop") == true) {
					if(g_system_application.getRunlevel() >= RunlevelRunning) {
						g_system_application.delEnv("gui/screen:animations/loop");
					}
				}
				response.clear();
				response["result"] = "OK";
				response["screen"] = gui_screen_getname();
				g_util_webserial.send("gui/screen", response);
		}
	}
	if(animations.empty() == true) {
		gui_screen_set("none", gui_screen_none);
		return validity;
	}
	animation_current = &animations.front();
	if((millis()-validity) < (animation_current->duration/animation_current->frames)) {
		return validity;
	}
	if(animation_current_frame >= animation_current->frames) {
		animation_current_frame = 0;
		if(animation_current->loop == true) {
			if(g_system_application.hasEnv("gui/screen:animations/loop") == true) {
				if(g_system_application.getEnv("gui/screen:animations/loop").compare("false") == 0) {
					g_system_application.delEnv("gui/screen:animations/loop");
					animation_current->loop = false;
				}
			}
		}
		if(animation_current->loop == false) {
			if(animation_current->onnext_webserial.empty() == false) {
				g_util_webserial.handle(animation_current->onnext_webserial);
			}
			animations.pop_front();
			if(animations.empty() == true) {
				animation_current = nullptr;
				return validity;
			}
			animation_current = &animations.front();
		}
	}
	if(animation_current_frame == 0) {
		if(animation_current->onthis_webserial.empty() == false) {
			g_util_webserial.handle(animation_current->onthis_webserial);
			animation_current->onthis_webserial.clear();
		}
	}
	if(gui == &g_gui_buffer) {
		static etl::string<GLOBAL_FILENAME_SIZE> filename;
		static etl::format_spec                  frame_format(10, 2, 0, false, false, false, false, '0');

		filename = animation_current->directory;
		if(filename.back() != '/') {
			filename += "/";
		}
		etl::to_string(animation_current_frame, filename, frame_format, true);
		filename += ".jpg";
		util_jpeg_decode565_littlefs(filename.c_str(), (uint16_t*)g_gui_buffer.getPointer(), GUI_SCREEN_WIDTH*GUI_SCREEN_HEIGHT*sizeof(uint16_t));
	} else {
		if(animation_current_frame == 0 || validity == GUI_INVALIDATED) {
			g_gui.fillScreen(TFT_BLACK);
			g_gui.setTextColor(TFT_RED, TFT_BLACK, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(3);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.drawString(animation_current->title.c_str(), g_gui.width()/2, g_gui.height()/2);
		}
	}
	animation_current_frame++;
	return millis();
}


static void gui_screen_animations_load(const etl::string<GLOBAL_FILENAME_SIZE>& filename, animations_t& animations) {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> animationsJSON;
	       File file;

	animations.clear();
	animationsJSON.clear();
	if(LittleFS.exists(filename.c_str()) == false) {
		g_system_application.processError("error", "217", "Animation error", filename);
		return;
	}
	file = LittleFS.open(filename.c_str(), "r");
	if(deserializeJson(animationsJSON, file) != DeserializationError::Ok) {
		g_system_application.processError("error", "217", "Animation error", filename);
		file.close();
		return;
	}
	file.close();
	for(JsonVariant animationJSON : animationsJSON.as<JsonArray>()) {
		static animation_t animation;

		animation.title.clear();
		animation.duration = 0;
		animation.directory.clear();
		animation.frames = 0;
		animation.loop = false;
		animation.onthis_webserial.clear();
		animation.onnext_webserial.clear();
		if(animationJSON.containsKey("title") == true) {
			animation.title = animationJSON["title"].as<const char*>();
		}
		if(animationJSON.containsKey("duration") == true) {
			animation.duration = animationJSON["duration"].as<unsigned long>();
		}
		if(animationJSON.containsKey("directory") == true) {
			animation.directory = animationJSON["directory"].as<const char*>();
		}
		if(animationJSON.containsKey("frames") == true) {
			animation.frames = animationJSON["frames"].as<unsigned int>();
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
		if(animation.directory.empty() == true || animation.frames == 0) {
			g_system_application.processError("error", "217", "Animation data error", filename);
			return;
		}
		animations.push_back(animation);
	}
}


unsigned long gui_screen_animations_system_booting(unsigned long validity, TFT_eSPI* gui) {
	g_system_application.setEnv("gui/screen:animations/name", "system-booting");
	gui_screen_set("animations:system-booting", gui_screen_animations);
	return millis();
}


unsigned long gui_screen_animations_system_configuring(unsigned long validity, TFT_eSPI* gui) {
	g_system_application.setEnv("gui/screen:animations/name", "system-configuring");
	gui_screen_set("animations:system-configuring", gui_screen_animations);
	return millis();
}


unsigned long gui_screen_animations_system_starting(unsigned long validity, TFT_eSPI* gui) {
	g_system_application.setEnv("gui/screen:animations/name", "system-starting");
	gui_screen_set("animations:system-starting", gui_screen_animations);
	return millis();
}


unsigned long gui_screen_animations_system_terminating(unsigned long validity, TFT_eSPI* gui) {
	g_system_application.setEnv("gui/screen:animations/name", "system-terminating");
	gui_screen_set("animations:system-terminating", gui_screen_animations);
	return millis();
}

