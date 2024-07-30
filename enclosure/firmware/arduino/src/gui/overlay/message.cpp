#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


gui_refresh_t gui_overlay_message(bool refresh) {
	static etl::string<GLOBAL_VALUE_SIZE>  message;
	       gui_refresh_t gui_refresh = RefreshIgnore;

	if(refresh == true) {
		message.clear();
	}
	if(message.compare(g_application.getEnv("gui/overlay:message/text")) != 0) {
		message = g_application.getEnv("gui/overlay:message/text");
		g_gui_overlay.fillSprite(TFT_TRANSPARENT);
		g_gui_overlay.setTextColor(TFT_WHITE, TFT_BLACK, false);
		g_gui_overlay.setTextFont(1);
		g_gui_overlay.setTextSize(2);
		g_gui_overlay.setTextDatum(MC_DATUM);
		g_gui_overlay.drawString(message.c_str(), (g_gui_overlay.width()-GUI_SCREEN_WIDTH)/2+(GUI_SCREEN_WIDTH/2),
		                                          (g_gui_overlay.height()-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*5));
		gui_refresh = RefreshAll;
	}
	return gui_refresh;
}

