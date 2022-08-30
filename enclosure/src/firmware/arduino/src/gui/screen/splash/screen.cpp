#include "util/jpeg.h"
#include "gui/screen/screen.h"
#include "globals.h"


void gui_screen_splash(bool force_refresh) {
	char filename[256] = {0};

	snprintf(filename, sizeof(filename), "/images/splash/%s", g_system_status["gui/screen:splash/filename"]);
	util_jpeg_decode565_littlefs(filename, g_gui_tft_buffer, TFT_WIDTH*TFT_HEIGHT);
	g_gui_tft.pushImage(0, 0, TFT_WIDTH, TFT_HEIGHT, (uint16_t*)g_gui_tft_buffer);
}

