#include "util/jpeg.h"
#include "gui/screen/screen.h"
#include "globals.h"


void gui_screen_splash(bool refresh) {
	if(refresh == true) {
		std::string filename("/images/splash/");

		filename += g_system_runtime["gui/screen:splash/filename"];
		util_jpeg_decode565_littlefs(filename.c_str(), g_gui_tft_buffer, TFT_WIDTH*TFT_HEIGHT);
		g_gui_tft.pushImage(0, 0, TFT_WIDTH, TFT_HEIGHT, (uint16_t*)g_gui_tft_buffer);
	}
}

