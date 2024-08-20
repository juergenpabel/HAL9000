#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void gui_update() {
	int gui_refresh = RefreshIgnore;

	gui_refresh |= gui_screen_update(false);
	gui_refresh |= gui_overlay_update(false);
	if(g_gui_screen.getPointer() != nullptr) {
		uint16_t offset_x = (g_gui.width() -GUI_SCREEN_WIDTH )/2;
		uint16_t offset_y = (g_gui.height()-GUI_SCREEN_HEIGHT)/2;

		switch(gui_refresh & RefreshScreen) {
			case RefreshScreen:
				g_device_microcontroller.mutex_enter("gpio");
				g_gui_screen.pushSprite(offset_x, offset_y);
				if(g_gui_overlay.getPointer() != nullptr) {
					g_gui_overlay.pushSprite(offset_x, offset_y, TFT_TRANSPARENT);
				} else {
					gui_overlay_update(true);
				}
				g_device_microcontroller.mutex_leave("gpio");
				break;
			default:
				if((gui_refresh & RefreshOverlay) == RefreshOverlay) {
					g_device_microcontroller.mutex_enter("gpio");
					if(g_gui_overlay.getPointer() != nullptr) {
						g_gui_overlay.pushSprite(offset_x, offset_y, TFT_TRANSPARENT);
					} else {
						gui_overlay_update(true);
					}
					g_device_microcontroller.mutex_leave("gpio");
				}
		}
	}
}

