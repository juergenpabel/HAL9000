#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/screen/screen.h"
#include "gui/screen/qrcode/screen.h"
#include "globals.h"


void gui_screen_error(bool refresh) {
	etl::string<GLOBAL_VALUE_SIZE> error_message;
	etl::string<GLOBAL_VALUE_SIZE> error_url;
	etl::string<GLOBAL_VALUE_SIZE> error_code;

	if(refresh == true) {
		if(g_application.hasEnv("gui/screen:error/message") == true) {
			error_message = g_application.getEnv("gui/screen:error/message");
		}
		if(g_application.hasEnv("gui/screen:error/url") == true) {
			error_url = g_application.getEnv("gui/screen:error/url");
		} else {
			error_url = "https://github.com/juergenpabel/HAL9000/wiki/Error-database";
		}
		if(g_application.hasEnv("gui/screen:error/code") == true) {
			error_code = "Error: ";
			error_code.append(g_application.getEnv("gui/screen:error/code"));
		}
		g_application.setEnv("gui/screen:qrcode/color-screen",   "red");
		g_application.setEnv("gui/screen:qrcode/color-text",     "white");
		g_application.setEnv("gui/screen:qrcode/textsize-above", "small");
		g_application.setEnv("gui/screen:qrcode/textsize-below", "normal");

		g_application.setEnv("gui/screen:qrcode/text-above", error_message);
		g_application.setEnv("gui/screen:qrcode/text-url",   error_url);
		g_application.setEnv("gui/screen:qrcode/text-below", error_code);
		gui_screen_qrcode(true);
		g_application.delEnv("gui/screen:qrcode/text-below");
		g_application.delEnv("gui/screen:qrcode/text-url");
		g_application.delEnv("gui/screen:qrcode/text-above");

		g_application.delEnv("gui/screen:qrcode/textsize-below");
		g_application.delEnv("gui/screen:qrcode/textsize-above");
		g_application.delEnv("gui/screen:qrcode/color-text");
		g_application.delEnv("gui/screen:qrcode/color-screen");
	}
}

