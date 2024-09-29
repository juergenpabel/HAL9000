#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "gui/screen/menu/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"

#define RADIUS_MIN (GUI_SCREEN_WIDTH/2 - 15)
#define RADIUS_MAX (GUI_SCREEN_WIDTH/2 -  5)


unsigned long gui_overlay_volume(unsigned long validity, TFT_eSPI* gui) {
	static uint8_t  previous_volume_level = 255;
	static uint16_t previous_volume_color = TFT_BLACK;
	       uint16_t volume_color = TFT_WHITE;
	       uint8_t  volume_level = 0;
	       uint16_t log_ctr_x = GUI_SCREEN_WIDTH /2;
	       uint16_t log_ctr_y = GUI_SCREEN_HEIGHT/2;

	if(g_system_application.hasEnv("gui/overlay:volume/level") == true) {
		volume_level = atoi(g_system_application.getEnv("gui/overlay:volume/level").c_str());
		if(volume_level != previous_volume_level) {
			previous_volume_level = volume_level;
			validity = GUI_INVALIDATED;
		}
	}
	if(g_system_application.getEnv("gui/overlay:volume/mute").compare("true") == 0) {
		volume_color = TFT_RED;
		if(volume_color != previous_volume_color) {
			previous_volume_color = volume_color;
			validity = GUI_INVALIDATED;
		}
	}
	if(g_system_application.getEnv("gui/overlay:volume/mute").compare("false") == 0) {
		volume_color = TFT_WHITE;
		if(volume_color != previous_volume_color) {
			previous_volume_color = volume_color;
			validity = GUI_INVALIDATED;
		}
	}
	if(validity == GUI_INVALIDATED) {
		for(uint8_t d=0; d<volume_level; d++) {
			double dx, dy;

			dx = cos(2*PI * d/100 * 6/8 + (2*PI*3/8));
			dy = sin(2*PI * d/100 * 6/8 + (2*PI*3/8));
			gui->drawLine(log_ctr_x+(dx*RADIUS_MIN), log_ctr_y+(dy*RADIUS_MIN), log_ctr_x+(dx*RADIUS_MAX), log_ctr_y+(dy*RADIUS_MAX), volume_color );
		}
		return millis();
	}
	return validity;
}

