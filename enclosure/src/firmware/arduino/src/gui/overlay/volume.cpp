#include <string>
#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"

static uint16_t      g_gui_overlay_icon[GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT];

#define CENTER_X   (TFT_WIDTH/2)
#define CENTER_Y   (TFT_HEIGHT/2)
#define RADIUS_MIN (TFT_WIDTH/2-15)
#define RADIUS_MAX (TFT_WIDTH/2- 5)


void gui_overlay_volume(bool refresh) {
	if(g_system_runtime.count("gui/overlay:volume/mute") == 1) {
		if(g_system_runtime["gui/overlay:volume/mute"] == std::string("false")) {
			uint8_t  volume_level = SYSTEM_STATUS_VOLUME;

			if(g_system_runtime.count("gui/overlay:volume/level") == 1) {
				volume_level = std::stoi(g_system_runtime["gui/overlay:volume/level"]);
			}
			for(uint8_t d=0; d<=100; d+=1) {
				double v = 0;
				double dx = TFT_WIDTH/2;
				double dy = TFT_HEIGHT/2;

				v = 2*PI * d/100 * 6/8 + (2*PI*3/8);
				dx = cos(v);
				dy = sin(v);
				if(volume_level > 0 && d<=volume_level) {
					g_gui_tft_overlay.drawLine(CENTER_X+(dx*RADIUS_MIN), CENTER_Y+(dy*RADIUS_MIN), CENTER_X+(dx*RADIUS_MAX), CENTER_Y+(dy*RADIUS_MAX), TFT_WHITE );
				} else {
					g_gui_tft_overlay.drawLine(CENTER_X+(dx*RADIUS_MIN), CENTER_Y+(dy*RADIUS_MIN), CENTER_X+(dx*RADIUS_MAX), CENTER_Y+(dy*RADIUS_MAX), TFT_BLACK );
					g_gui_tft.drawLine        (CENTER_X+(dx*RADIUS_MIN), CENTER_Y+(dy*RADIUS_MIN), CENTER_X+(dx*RADIUS_MAX), CENTER_Y+(dy*RADIUS_MAX), TFT_BLACK );
				}
			}
//TODO			util_jpeg_decode565_littlefs("/images/overlay/volume/speaker.jpg", g_gui_overlay_icon, GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT);
//TODO			for(int y=0; y<GUI_OVERLAY_ICON_HEIGHT; y++) {
//TODO				for(int x=0; x<GUI_OVERLAY_ICON_WIDTH; x++) {
//TODO					if(g_gui_overlay_icon[y*GUI_OVERLAY_ICON_WIDTH+x] != TFT_BLACK) {
//TODO						g_gui_tft.drawPixel(x, y, TFT_WHITE);
//TODO					}
//TODO				}
//TODO			}
//TODO			g_gui_tft_overlay.pushImage(CENTER_X-(GUI_OVERLAY_ICON_WIDTH/2), CENTER_Y+(CENTER_Y/2)-(GUI_OVERLAY_ICON_HEIGHT/2), GUI_OVERLAY_ICON_WIDTH, GUI_OVERLAY_ICON_HEIGHT, g_gui_overlay_icon);
		} else {
//TODO			util_jpeg_decode565_littlefs("/images/overlay/volume/speaker-mute.jpg", g_gui_overlay_icon, GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT);
//TODO			for(int y=0; y<GUI_OVERLAY_ICON_HEIGHT; y++) {
//TODO				for(int x=0; x<GUI_OVERLAY_ICON_WIDTH; x++) {
//TODO					if(g_gui_overlay_icon[y*GUI_OVERLAY_ICON_WIDTH+x] != TFT_BLACK) {
//TODO						g_gui_tft_overlay.drawPixel(x, y, TFT_WHITE);
//TODO					}
//TODO				}
//TODO			}
		}
	}
}

