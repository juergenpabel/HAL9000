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
	etl::string<GLOBAL_VALUE_SIZE>     title;
	unsigned long                      duration;
	etl::string<GLOBAL_FILENAME_SIZE>  directory;
	unsigned int                       frames;
	boolean                            loop;
	etl::string<GLOBAL_VALUE_SIZE>     on_this;
	etl::string<GLOBAL_VALUE_SIZE>     on_next;
} animation_t;

static etl::string<GLOBAL_VALUE_SIZE> g_animations_name;
static etl::list<animation_t, 8>      g_animations_data;

static void gui_screen_animations_load(const etl::string<GLOBAL_VALUE_SIZE>& name, const etl::string<GLOBAL_FILENAME_SIZE>& filename);


unsigned long gui_screen_animations(unsigned long validity, TFT_eSPI* gui) {
	static bool          webserial_delayed_response = false;
	static unsigned int  animation_current_frame = 0;
	       animation_t*  animation_current = nullptr;

	if(validity == GUI_RELOAD) {
		webserial_delayed_response = false;
		g_animations_name.clear();
		g_animations_data.clear();
		return GUI_INVALIDATED;
	}
	if(validity == GUI_INVALIDATED) {
		if(g_animations_data.empty() == true) {
			if(g_system_application.hasEnv("gui/screen:animations/name") == false) {
				static etl::string<GLOBAL_VALUE_SIZE> animation;

				animation = gui_screen_getname();
				if(animation.compare(0, 11, "animations:") == 0) {
					animation = animation.substr(11, animation.npos);
					g_system_application.setEnv("gui/screen:animations/name", animation);
				}
			}
			if(g_animations_name.empty() == false) {
				webserial_delayed_response = true;
			}
		}
	}
	if(g_system_application.hasEnv("gui/screen:animations/name") == true) {
		static etl::string<GLOBAL_VALUE_SIZE>          animation;
		static etl::string<GLOBAL_FILENAME_SIZE>       filename;
		static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

		animation = g_system_application.getEnv("gui/screen:animations/name");
		switch(g_animations_data.empty()) {
			case false:
				for(etl::list<animation_t, 8>::iterator iter=g_animations_data.begin(); iter!=g_animations_data.end(); ++iter) {
					if(iter->loop == true) {
						iter->loop = false;
					}
				}
				break;
			case true:
				animation_current_frame = 0;
				filename  = "/gui/screen/animations/";
				filename += animation;
				filename += ".json";
				if(gui != &g_gui) {
					g_device_microcontroller.mutex_enter("gpio");
				}
				gui_screen_animations_load(animation, filename);
				if(gui != &g_gui) {
					g_device_microcontroller.mutex_leave("gpio");
				}
				if(g_animations_data.empty() == true) {
					g_system_application.addErrorContext("gui_screen_animations(): gui_screen_animations_load() returned " \
					                     "empty set for: 'TODO:filename'");
					return GUI_ERROR;
				}
				if(g_system_application.hasEnv("gui/screen:animations/loop") == true) {
					if(animation.compare(g_system_application.getEnv("gui/screen:animations/loop")) != 0) {
						g_system_application.delEnv("gui/screen:animations/loop");
					}
				}
				animation.insert(0, "animations:");
				gui_screen_set(animation, gui_screen_animations);
				if(webserial_delayed_response == true) {
					response.clear();
					response["screen"] = animation;
					g_util_webserial.send("gui/screen", response);
					webserial_delayed_response = false;
				}
				g_system_application.delEnv("gui/screen:animations/name");
				break;
		}
	}
	if(g_animations_data.empty() == true) {
		gui_screen_set("none", gui_screen_none);
		return validity;
	}
	animation_current = &g_animations_data.front();
	if((millis()-validity) < (animation_current->duration/animation_current->frames)) {
		return validity;
	}
	if(animation_current_frame >= animation_current->frames) {
		animation_current_frame = 0;
		if(animation_current->loop == true) {
			if(g_system_application.hasEnv("gui/screen:animations/loop") == true) {
				static etl::string<GLOBAL_VALUE_SIZE> animation;

				animation.clear();
				animation = gui_screen_getname();
				if(animation.compare(11, animation.npos, g_system_application.getEnv("gui/screen:animations/loop")) == 0) {
					g_system_application.delEnv("gui/screen:animations/loop");
					animation_current->loop = false;
				}
			}
		}
		if(animation_current->loop == false) {
			if(animation_current->on_next.empty() == false) {
				if(animation_current->on_next.compare(0, 22, "util/webserial:handle=") == 0) {
					animation_current->on_next.erase(0, 22);
					g_util_webserial.handle(animation_current->on_next);
					animation_current->on_next.clear();
				}
				if(animation_current->on_next.compare(0, 25, "gui/overlay:message/text=") == 0) {
					animation_current->on_next.erase(0, 25);
					g_system_application.setEnv("gui/overlay:message/text", animation_current->on_next);
					gui_overlay_set("message", gui_overlay_message);
					animation_current->on_next.clear();
				}
			}
			g_animations_data.pop_front();
			if(g_animations_data.empty() == true) {
				animation_current = nullptr;
				return validity;
			}
			animation_current = &g_animations_data.front();
		}
	}
	if(animation_current_frame == 0) {
		if(animation_current->on_this.empty() == false) {
			if(animation_current->on_this.compare(0, 22, "util/webserial:handle=") == 0) {
				animation_current->on_this.erase(0, 22);
				g_util_webserial.handle(animation_current->on_this);
				animation_current->on_this.clear();
			}
			if(animation_current->on_this.compare(0, 25, "gui/overlay:message/text=") == 0) {
				animation_current->on_this.erase(0, 25);
				g_system_application.setEnv("gui/overlay:message/text", animation_current->on_this);
				gui_overlay_set("message", gui_overlay_message);
				animation_current->on_this.clear();
			}
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


static void gui_screen_animations_load(const etl::string<GLOBAL_VALUE_SIZE>& name, const etl::string<GLOBAL_FILENAME_SIZE>& filename) {
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> animationsJSON;
	       File file;

	g_animations_name.clear();
	g_animations_data.clear();
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
		animation.on_this.clear();
		animation.on_next.clear();
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
			for(JsonPair on_this : animationJSON["on:this"].as<JsonObject>()) {
				animation.on_this  = on_this.key().c_str();
				animation.on_this += "=";
				animation.on_this += on_this.value().as<const char*>();
			}
		}
		if(animationJSON.containsKey("on:next") == true) {
			for(JsonPair on_next : animationJSON["on:next"].as<JsonObject>()) {
				animation.on_next  = on_next.key().c_str();
				animation.on_next += "=";
				animation.on_next += on_next.value().as<const char*>();
			}
		}
		if(animation.directory.empty() == true || animation.frames == 0) {
			g_system_application.processError("error", "217", "Animation data error", filename);
			return;
		}
		g_animations_name = name;
		g_animations_data.push_back(animation);
	}
}

