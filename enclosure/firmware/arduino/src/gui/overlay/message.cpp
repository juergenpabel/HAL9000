#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


unsigned long gui_overlay_message(unsigned long lastDraw, TFT_eSPI* gui) {
	static etl::string<GLOBAL_VALUE_SIZE>  message;

	if(lastDraw == GUI_UPDATE) {
		message = g_application.getEnv("gui/overlay:message/text");
		gui->setTextColor(TFT_WHITE, TFT_BLACK, false);
		gui->setTextFont(1);
		gui->setTextSize(2);
		gui->setTextDatum(MC_DATUM);
		gui->drawString(message.c_str(), (gui->width()-GUI_SCREEN_WIDTH)/2+(GUI_SCREEN_WIDTH/2), (gui->height()-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*5));
		return millis();
	}
	return lastDraw;
}

