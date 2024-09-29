#include <ArduinoJson.h>
#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/screen/qrcode/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


unsigned long gui_screen_error(unsigned long validity, TFT_eSPI* gui) {
	etl::string<GLOBAL_VALUE_SIZE> error_title;
	etl::string<GLOBAL_VALUE_SIZE> error_url;
	etl::string<GLOBAL_VALUE_SIZE> error_id;

	if(validity == GUI_INVALIDATED) {
		unsigned long currentDraw = GUI_INVALIDATED;

		if(gui_overlay_get() != gui_overlay_none) {
			gui_overlay_set("none", gui_overlay_none);
		}
		if(g_system_application.hasEnv("gui/screen:error/id") == true) {
			error_id = g_system_application.getEnv("gui/screen:error/id");
		}
		if(g_system_application.hasEnv("gui/screen:error/url") == true) {
			error_url = g_system_application.getEnv("gui/screen:error/url");
		} else {
			error_url = g_system_application.getSetting("system/error:url/template");
			if(error_id.empty() == false) {
				size_t url_id_offset;

				url_id_offset = error_url.find("{error_id}");
				if(url_id_offset != error_url.npos) {
					error_url = error_url.replace(url_id_offset, 10, error_id);
				}
			}
		}
		if(g_system_application.hasEnv("gui/screen:error/title") == true) {
			error_title = g_system_application.getEnv("gui/screen:error/title");
		}
		g_system_application.setEnv("gui/screen:qrcode/color-screen",   "red");
		g_system_application.setEnv("gui/screen:qrcode/color-text",     "white");
		g_system_application.setEnv("gui/screen:qrcode/textsize-above", "small");
		g_system_application.setEnv("gui/screen:qrcode/textsize-below", "normal");
		g_system_application.setEnv("gui/screen:qrcode/text-above", error_title);
		g_system_application.setEnv("gui/screen:qrcode/text-url",   error_url);
		g_system_application.setEnv("gui/screen:qrcode/text-below", error_id.insert(0, "Error: "));
		currentDraw = gui_screen_qrcode(validity, gui);
		g_system_application.delEnv("gui/screen:qrcode/text-below");
		g_system_application.delEnv("gui/screen:qrcode/text-url");
		g_system_application.delEnv("gui/screen:qrcode/text-above");
		g_system_application.delEnv("gui/screen:qrcode/textsize-below");
		g_system_application.delEnv("gui/screen:qrcode/textsize-above");
		g_system_application.delEnv("gui/screen:qrcode/color-text");
		g_system_application.delEnv("gui/screen:qrcode/color-screen");
		return currentDraw;
	}
	return validity;
}

