#include "gui/screen/screen.h"
#include "gui/screen/splash/screen.h"
#include "util/jpeg.h"
#include "globals.h"


void gui_screen_splash_jpeg(const char* filename) {
	g_previous_screen = screen_set(screen_splash);
	util_jpeg_decode565_littlefs(filename, g_gui_tft_buffer, TFT_WIDTH*TFT_HEIGHT);
	g_gui_tft.pushImage(0, 0, TFT_WIDTH, TFT_HEIGHT, (uint16_t*)g_gui_tft_buffer);
}

