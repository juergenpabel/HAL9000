#include "gui/gui.h"
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "globals.h"


void gui_update() {
	static unsigned long previousScreenDraw = GUI_UPDATE;
	static unsigned long previousOverlayDraw = GUI_UPDATE;
	       unsigned long currentScreenDraw = GUI_UPDATE;
	       unsigned long currentOverlayDraw = GUI_UPDATE;
	       TFT_eSPI*     gui = nullptr;

	gui = &g_gui_buffer;
	if(g_gui_buffer.getPointer() == nullptr) {
		gui = &g_gui;
	}
	if(gui == &g_gui) {
		g_device_microcontroller.mutex_enter("gpio");
	}
	currentScreenDraw = gui_screen_update(previousScreenDraw, gui);
	if(currentScreenDraw != previousScreenDraw) {
		previousOverlayDraw = GUI_UPDATE;
	}
	currentOverlayDraw = gui_overlay_update(previousOverlayDraw, gui);
	if(currentOverlayDraw == GUI_UPDATE) {
		previousScreenDraw = GUI_UPDATE;
	}
	if(gui == &g_gui) {
		g_device_microcontroller.mutex_leave("gpio");
	}
	if(previousScreenDraw == GUI_UPDATE || previousOverlayDraw == GUI_UPDATE || currentScreenDraw != previousScreenDraw || currentOverlayDraw != previousOverlayDraw) {
		if(gui == &g_gui_buffer) {
			uint16_t offset_x = (g_gui.width() -GUI_SCREEN_WIDTH )/2;
			uint16_t offset_y = (g_gui.height()-GUI_SCREEN_HEIGHT)/2;

			g_device_microcontroller.mutex_enter("gpio");
			g_gui_buffer.pushSprite(offset_x, offset_y);
			g_device_microcontroller.mutex_leave("gpio");
		}
		previousScreenDraw = currentScreenDraw;
		previousOverlayDraw = currentOverlayDraw;
	}
}

