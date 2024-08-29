#include <ArduinoJson.h>
#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/screen/qrcode/screen.h"
#include "application/error.h"
#include "globals.h"


unsigned long gui_screen_error(unsigned long lastDraw, TFT_eSPI* gui) {
	etl::string<GLOBAL_VALUE_SIZE> error_message;
	etl::string<GLOBAL_VALUE_SIZE> error_url;
	etl::string<GLOBAL_VALUE_SIZE> error_id;

	if(lastDraw == GUI_UPDATE) {
		unsigned long currentDraw = GUI_UPDATE;

		if(g_application.hasEnv("gui/screen:error/id") == true) {
			error_id = g_application.getEnv("gui/screen:error/id");
		}
		if(g_application.hasEnv("gui/screen:error/url") == true) {
			error_url = g_application.getEnv("gui/screen:error/url");
		} else {
			error_url = Error::calculateURL(error_id);
		}
		if(g_application.hasEnv("gui/screen:error/message") == true) {
			error_message = g_application.getEnv("gui/screen:error/message");
		}
		g_application.setEnv("gui/screen:qrcode/color-screen",   "red");
		g_application.setEnv("gui/screen:qrcode/color-text",     "white");
		g_application.setEnv("gui/screen:qrcode/textsize-above", "small");
		g_application.setEnv("gui/screen:qrcode/textsize-below", "normal");
		g_application.setEnv("gui/screen:qrcode/text-above", error_message);
		g_application.setEnv("gui/screen:qrcode/text-url",   error_url);
		g_application.setEnv("gui/screen:qrcode/text-below", error_id.insert(0, "Error: "));
		currentDraw = gui_screen_qrcode(lastDraw, gui);
		g_application.delEnv("gui/screen:qrcode/text-below");
		g_application.delEnv("gui/screen:qrcode/text-url");
		g_application.delEnv("gui/screen:qrcode/text-above");
		g_application.delEnv("gui/screen:qrcode/textsize-below");
		g_application.delEnv("gui/screen:qrcode/textsize-above");
		g_application.delEnv("gui/screen:qrcode/color-text");
		g_application.delEnv("gui/screen:qrcode/color-screen");
		return currentDraw;
	}
	return lastDraw;
}

