#include "util/jpeg.h"
#include "gui/screen/screen.h"
#include "globals.h"


void gui_screen_error(bool refresh) {
	if(refresh == true) {
		etl::string<GLOBAL_FILENAME_SIZE> filename("/images/error/");

		filename += g_application.getEnv("gui/screen:error/filename");
		util_jpeg_decode565_littlefs(filename, g_gui_buffer, GUI_SCREEN_WIDTH*GUI_SCREEN_HEIGHT*sizeof(uint16_t));
		g_gui.pushImage((TFT_WIDTH-GUI_SCREEN_WIDTH)/2, (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2, GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT, (uint16_t*)g_gui_buffer);
	}
}

