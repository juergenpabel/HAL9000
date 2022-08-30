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


void gui_overlay_volume(bool force_refresh) {
	if(g_system_status["system/audio:volume/mute"] == std::string("False")) {
		uint8_t  volume_level;

		volume_level = std::stoi(g_system_status["system/audio:volume/level"]);
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
//TODO		util_jpeg_decode565_littlefs("/images/overlay/volume/speaker.jpg", g_gui_overlay_icon, GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT);
		for(int y=0; y<GUI_OVERLAY_ICON_HEIGHT; y++) {
			for(int x=0; x<GUI_OVERLAY_ICON_WIDTH; x++) {
				if(g_gui_overlay_icon[y*GUI_OVERLAY_ICON_WIDTH+x] != TFT_BLACK) {
					g_gui_tft.drawPixel(x, y, TFT_WHITE);
				}
			}
		}
//		g_gui_tft_overlay.pushImage(CENTER_X-(GUI_OVERLAY_ICON_WIDTH/2), CENTER_Y+(CENTER_Y/2)-(GUI_OVERLAY_ICON_HEIGHT/2), GUI_OVERLAY_ICON_WIDTH, GUI_OVERLAY_ICON_HEIGHT, g_gui_overlay_icon);
	} else {
		util_jpeg_decode565_littlefs("/images/overlay/volume/speaker-mute.jpg", g_gui_overlay_icon, GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT);
		for(int y=0; y<GUI_OVERLAY_ICON_HEIGHT; y++) {
			for(int x=0; x<GUI_OVERLAY_ICON_WIDTH; x++) {
				if(g_gui_overlay_icon[y*GUI_OVERLAY_ICON_WIDTH+x] != TFT_BLACK) {
					g_gui_tft_overlay.drawPixel(x, y, TFT_WHITE);
				}
			}
		}
	}
}
