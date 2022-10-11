#include "util/jpeg.h"
#include "gui/screen/screen.h"
#include "globals.h"


void gui_screen_splash(bool refresh) {
	if(refresh == true) {
		etl::string<GLOBAL_FILENAME_SIZE> filename("/images/splash/");

		filename += g_system_runtime["gui/screen:splash/filename"];
		util_jpeg_decode565_littlefs(filename, g_gui_buffer, GUI_SCREEN_WIDTH*GUI_SCREEN_HEIGHT);
		g_gui.pushImage((TFT_WIDTH-GUI_SCREEN_WIDTH)/2, (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2, GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT, (uint16_t*)g_gui_buffer);
	}
}

