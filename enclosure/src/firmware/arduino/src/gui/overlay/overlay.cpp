#include <string.h>
#include <TimeLib.h>
#include <LittleFS.h>
#include <SimpleWebSerial.h>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "gui/util/png.h"
#include "globals.h"

static overlay_update_func  g_current_update_func = overlay_update_none;
static uint16_t             g_overlay_icon[GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT];

overlay_update_func overlay_update(overlay_update_func new_update_func) {
	overlay_update_func previous_update_func = NULL;

	if(new_update_func != NULL) {
		previous_update_func = g_current_update_func;
		g_current_update_func = new_update_func;
		screen_update(screen_update_noop, true);
	}
	g_current_update_func();
	return previous_update_func;
}


void overlay_update_noop() {
}


void overlay_update_none() {
	g_gui_tft_overlay.fillSprite(TFT_TRANSPARENT);
}


void overlay_update_volume() {
	g_gui_tft_overlay.fillSprite(TFT_TRANSPARENT);
	g_gui_tft_overlay.setTextColor(TFT_WHITE, TFT_TRANSPARENT);
	if(String("False").equals(g_system_settings["audio:volume-mute"])) {
		uint8_t  volume_level;

		volume_level = g_system_settings["audio:volume-level"].toInt();
		for(uint8_t d=0; d<volume_level; d++) {
			double v = 0;
			double dx = TFT_WIDTH/2;
			double dy = TFT_HEIGHT/2;

			v = 2 * PI * d / 100;
			dx = cos(v);
			dy = sin(v);
			g_gui_tft_overlay.drawLine((TFT_WIDTH/2)+(dx*100), (TFT_HEIGHT/2)+(dy*100), (TFT_WIDTH/2)+(dx*115), (TFT_WIDTH/2)+(dy*115), TFT_WHITE);
		}

		png_load_littlefs("/images/overlay/volume/speaker.png", GUI_OVERLAY_ICON_WIDTH, GUI_OVERLAY_ICON_HEIGHT, g_overlay_icon);
		g_gui_tft_overlay.pushImage((TFT_WIDTH/2)-(GUI_OVERLAY_ICON_WIDTH/2), (TFT_HEIGHT/4*3)-(GUI_OVERLAY_ICON_HEIGHT/2), GUI_OVERLAY_ICON_WIDTH, GUI_OVERLAY_ICON_HEIGHT, g_overlay_icon);
	} else {
		png_load_littlefs("/images/overlay/volume/speaker-mute.png", GUI_OVERLAY_ICON_WIDTH, GUI_OVERLAY_ICON_HEIGHT, g_overlay_icon);
		g_gui_tft_overlay.pushImage((TFT_WIDTH/2)-(GUI_OVERLAY_ICON_WIDTH/2), (TFT_HEIGHT/4*3)-(GUI_OVERLAY_ICON_HEIGHT/2), GUI_OVERLAY_ICON_WIDTH, GUI_OVERLAY_ICON_HEIGHT, g_overlay_icon);
	}
}


void overlay_update_message() {
}

