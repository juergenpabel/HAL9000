#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void gui_update() {
	static unsigned long prevScreenValidity = GUI_INVALIDATED;
	static unsigned long prevOverlayValidity = GUI_INVALIDATED;
	       unsigned long currentScreenValidity = GUI_INVALIDATED;
	       unsigned long currentOverlayValidity = GUI_INVALIDATED;
	       bool          gui_buffer_flush = false;
	       TFT_eSPI*     gui = nullptr;

	gui = &g_gui_buffer;
	if(g_gui_buffer.getPointer() == nullptr) {
		gui = &g_gui;
	}
	if(gui == &g_gui) {
		g_device_microcontroller.mutex_enter("gpio");
	}
	currentScreenValidity = gui_screen_update(prevScreenValidity, gui);
	if(currentScreenValidity == GUI_ERROR) {
		g_application.processError("error", "219", "GUI Error", gui_screen_getname());
		return;
	}
	if(prevScreenValidity != currentScreenValidity) {
		prevOverlayValidity = GUI_INVALIDATED;
		gui_buffer_flush = true;
	}
	currentOverlayValidity = gui_overlay_update(prevOverlayValidity, gui);
	if(currentOverlayValidity == GUI_ERROR) {
		g_application.processError("error", "219", "GUI Error", gui_overlay_getname());
		return;
	}
	if(prevOverlayValidity != currentOverlayValidity) {
		currentScreenValidity = GUI_INVALIDATED;
		gui_buffer_flush = true;
	}
	if(gui == &g_gui) {
		g_device_microcontroller.mutex_leave("gpio");
	}
	if(gui == &g_gui_buffer) {
		if(gui_buffer_flush == true) {
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

