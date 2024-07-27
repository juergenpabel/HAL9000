#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void gui_update() {
	bool refresh = false;

	refresh |= gui_screen_update(refresh);
	refresh |= gui_overlay_update(refresh);
	if(refresh == true && g_gui_screen.getPointer() != nullptr && g_gui_overlay.getPointer() != nullptr) {
		uint16_t offset_x = (g_gui.width() -GUI_SCREEN_WIDTH )/2;
		uint16_t offset_y = (g_gui.height()-GUI_SCREEN_HEIGHT)/2;

		g_device_microcontroller.mutex_enter("gpio");
		g_gui_screen.pushSprite(offset_x, offset_y);
		g_gui_overlay.pushSprite(offset_x, offset_y, TFT_BLACK);
		g_device_microcontroller.mutex_exit("gpio");
	}
}

