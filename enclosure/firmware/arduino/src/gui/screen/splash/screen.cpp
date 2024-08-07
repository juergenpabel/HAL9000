#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>

#include "gui/screen/screen.h"
#include "gui/screen/qrcode/screen.h"
#include "globals.h"


gui_refresh_t gui_screen_splash(bool refresh) {
	etl::string<GLOBAL_VALUE_SIZE> splash_message;
	etl::string<GLOBAL_VALUE_SIZE> splash_url;
	etl::string<GLOBAL_VALUE_SIZE> splash_id;
	gui_refresh_t                  gui_refresh = RefreshIgnore;

	if(refresh == true) {
		if(g_application.hasEnv("gui/screen:splash/id") == true) {
			splash_id = g_application.getEnv("gui/screen:splash/id");
		}
		if(g_application.hasEnv("gui/screen:splash/url") == true) {
			splash_url = g_application.getEnv("gui/screen:splash/url");
		} else {
			splash_url = "https://github.com/juergenpabel/HAL9000/wiki/Splashs"; //TODO: Splash::calculateURL(splash_id)
		}
		if(g_application.hasEnv("gui/screen:splash/message") == true) {
			splash_message = g_application.getEnv("gui/screen:splash/message");
		}
		g_application.setEnv("gui/screen:qrcode/color-screen",   "blue");
		g_application.setEnv("gui/screen:qrcode/color-text",     "white");
		g_application.setEnv("gui/screen:qrcode/textsize-above", "small");
		g_application.setEnv("gui/screen:qrcode/textsize-below", "normal");
		g_application.setEnv("gui/screen:qrcode/text-above", splash_message);
		g_application.setEnv("gui/screen:qrcode/text-url",   splash_url);
		g_application.setEnv("gui/screen:qrcode/text-below", splash_id.insert(0, "ID: "));
		gui_refresh = gui_screen_qrcode(refresh);
		g_application.delEnv("gui/screen:qrcode/text-below");
		g_application.delEnv("gui/screen:qrcode/text-url");
		g_application.delEnv("gui/screen:qrcode/text-above");
		g_application.delEnv("gui/screen:qrcode/textsize-below");
		g_application.delEnv("gui/screen:qrcode/textsize-above");
		g_application.delEnv("gui/screen:qrcode/color-text");
		g_application.delEnv("gui/screen:qrcode/color-screen");
	}
	return gui_refresh;
}

