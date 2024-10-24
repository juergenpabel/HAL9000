#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/screen/error/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void gui_update() {
	static unsigned long prevScreenValidity = GUI_INVALIDATED;
	static unsigned long prevOverlayValidity = GUI_INVALIDATED;
	       unsigned long currentScreenValidity = GUI_INVALIDATED;
	       unsigned long currentOverlayValidity = GUI_INVALIDATED;
	static bool          pseudoScreenError210 = false;
	       TFT_eSPI*     gui = nullptr;

	gui = &g_gui_buffer;
	if(g_gui_buffer.getPointer() == nullptr) {
		gui = &g_gui;
	}
	if(gui == &g_gui) {
		g_device_microcontroller.mutex_enter("gpio");
	}
	switch(g_util_webserial.wasAlive() == g_util_webserial.isAlive()) {
		case true:
			if(pseudoScreenError210 == true) {
				if(g_system_application.hasEnv("gui/screen:error/id") == true) {
					if(g_system_application.getEnv("gui/screen:error/id").compare("210") == 0) {
						g_system_application.delEnv("gui/screen:error/level");
						g_system_application.delEnv("gui/screen:error/id");
						g_system_application.delEnv("gui/screen:error/title");
					}
				}
				prevScreenValidity = GUI_INVALIDATED;
				pseudoScreenError210 = false;
			}
			currentScreenValidity = gui_screen_update(prevScreenValidity, gui);
			if(prevScreenValidity != currentScreenValidity) {
				prevOverlayValidity = GUI_INVALIDATED;
			}
			currentOverlayValidity = gui_overlay_update(prevOverlayValidity, gui);
			if(prevOverlayValidity != currentOverlayValidity) {
				currentScreenValidity = GUI_INVALIDATED;
			}
			break;
		case false:
			if(g_util_webserial.isAlive() == false) {
				if(pseudoScreenError210 == false) {
					if(g_system_application.hasEnv("gui/screen:error/id") == false) {
						g_system_application.setEnv("gui/screen:error/level", "error");
						g_system_application.setEnv("gui/screen:error/id", "210");
						g_system_application.setEnv("gui/screen:error/title", "Lost connection to host");
					}
					currentScreenValidity = gui_screen_error(GUI_INVALIDATED, gui);
					pseudoScreenError210 = true;
				}
			}
	}
	if(gui == &g_gui) {
		g_device_microcontroller.mutex_leave("gpio");
	}
	if(currentScreenValidity == GUI_ERROR) {
		g_system_application.processError("error", "219", "GUI Error (screen)", gui_screen_getname());
		return;
	}
	if(currentOverlayValidity == GUI_ERROR) {
		g_system_application.processError("error", "219", "GUI Error (overlay)", gui_overlay_getname());
		return;
	}
	if(gui == &g_gui_buffer) {
		if(prevScreenValidity != currentScreenValidity || prevOverlayValidity != currentOverlayValidity) {
			uint16_t offset_x = (g_gui.width() -GUI_SCREEN_WIDTH )/2;
			uint16_t offset_y = (g_gui.height()-GUI_SCREEN_HEIGHT)/2;

			g_device_microcontroller.mutex_enter("gpio");
			g_gui_buffer.pushSprite(offset_x, offset_y);
			g_device_microcontroller.mutex_leave("gpio");
		}
	}
	prevScreenValidity = currentScreenValidity;
	prevOverlayValidity = currentOverlayValidity;
}

