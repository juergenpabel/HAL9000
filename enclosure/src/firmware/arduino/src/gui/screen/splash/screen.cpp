#include "util/jpeg.h"
#include "gui/screen/screen.h"
#include "globals.h"


void gui_screen_splash(bool refresh) {
	if(refresh == true) {
		etl::string<GLOBAL_FILENAME_SIZE> filename("/images/splash/");

		filename += g_application.getEnv("gui/screen:splash/filename");
		if(g_gui_buffer != nullptr) {
			util_jpeg_decode565_littlefs(filename, g_gui_buffer, GUI_SCREEN_WIDTH*GUI_SCREEN_HEIGHT*sizeof(uint16_t));
			g_gui.pushImage((TFT_WIDTH-GUI_SCREEN_WIDTH)/2, (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2, GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT, (uint16_t*)g_gui_buffer);
		} else {
			g_gui.fillScreen(TFT_BLACK);
			g_gui.setTextColor(TFT_RED, TFT_BLACK, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(1);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.drawString(filename.c_str(), TFT_WIDTH/2, TFT_HEIGHT/2);
		}
	}
}

