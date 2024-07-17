#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


static gui_screen_func  g_gui_screen = gui_screen_none;
static bool             g_gui_screen_forced_refresh = false;


gui_screen_func gui_screen_get() {
	return g_gui_screen;
}


void gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func) {
	static etl::string<GLOBAL_VALUE_SIZE> payload;

	if(screen_func != nullptr && screen_func != g_gui_screen) {
		g_gui_screen = screen_func;
		g_gui_screen_forced_refresh = true;
		if(screen_name.size() > 0) {
			payload = "{\"screen\":\"<NAME>\"}";
			payload.replace(11, 6, screen_name);
			g_util_webserial.send("gui/event", payload, false);
		}
	}
}


void gui_screen_set_refresh() {
	g_gui_screen_forced_refresh = true;
}


void gui_screen_update(bool refresh) {
	uint16_t offset_x = (TFT_WIDTH-GUI_SCREEN_WIDTH)/2;
	uint16_t offset_y = (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2;

	if(g_gui_screen_forced_refresh == true) {
		refresh = true;
		g_gui_screen_forced_refresh = false;
	}
	gui_overlay_update(refresh);
	g_gui_screen(refresh);
	g_gui_overlay.pushSprite(offset_x, offset_y, TFT_BLACK);
}


void gui_screen_none(bool refresh) {
	(void)refresh;
}

