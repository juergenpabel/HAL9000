#include "gui/screen/screen.h"
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"

//TODO static uint16_t      g_gui_overlay_icon[GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT];

#define RADIUS_MIN (GUI_SCREEN_WIDTH/2 - 15)
#define RADIUS_MAX (GUI_SCREEN_WIDTH/2 -  5)


void gui_overlay_volume(bool refresh) {
	if(g_system_runtime.count("gui/overlay:volume/mute") == 1) {
		if(g_system_runtime["gui/overlay:volume/mute"].compare("false") == 0) {
			uint8_t  volume_level = SYSTEM_RUNTIME_VOLUME;
			uint16_t log_ctr_x = GUI_SCREEN_WIDTH /2;
			uint16_t log_ctr_y = GUI_SCREEN_HEIGHT/2;
			uint16_t phy_ctr_x = TFT_WIDTH /2;
			uint16_t phy_ctr_y = TFT_HEIGHT/2;

			if(g_system_runtime.count("gui/overlay:volume/level") == 1) {
				volume_level = atoi(g_system_runtime["gui/overlay:volume/level"].c_str());
			}
			for(uint8_t d=0; d<=100; d+=1) {
				double dx;
				double dy;

				dx = cos(2*PI * d/100 * 6/8 + (2*PI*3/8));
				dy = sin(2*PI * d/100 * 6/8 + (2*PI*3/8));
				if(volume_level > 0 && d<=volume_level) {
					g_gui_overlay.drawLine(log_ctr_x+(dx*RADIUS_MIN), log_ctr_y+(dy*RADIUS_MIN), log_ctr_x+(dx*RADIUS_MAX), log_ctr_y+(dy*RADIUS_MAX), TFT_WHITE );
				} else {
					g_gui_overlay.drawLine(log_ctr_x+(dx*RADIUS_MIN), log_ctr_y+(dy*RADIUS_MIN), log_ctr_x+(dx*RADIUS_MAX), log_ctr_y+(dy*RADIUS_MAX), TFT_BLACK );
					g_gui.drawLine        (phy_ctr_x+(dx*RADIUS_MIN), phy_ctr_y+(dy*RADIUS_MIN), phy_ctr_x+(dx*RADIUS_MAX), phy_ctr_y+(dy*RADIUS_MAX), TFT_BLACK );
				}
			}
//TODO			util_jpeg_decode565_littlefs("/images/overlay/volume/speaker.jpg", g_gui_overlay_icon, GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT);
//TODO			for(int y=0; y<GUI_OVERLAY_ICON_HEIGHT; y++) {
//TODO				for(int x=0; x<GUI_OVERLAY_ICON_WIDTH; x++) {
//TODO					if(g_gui_overlay_icon[y*GUI_OVERLAY_ICON_WIDTH+x] != TFT_BLACK) {
//TODO						g_gui.drawPixel(x, y, TFT_WHITE);
//TODO					}
//TODO				}
//TODO			}
//TODO			g_gui_overlay.pushImage(center_x-(GUI_OVERLAY_ICON_WIDTH/2), center_y+(GUI_SCREEN_HEIGHT/2)-(GUI_OVERLAY_ICON_HEIGHT/2), GUI_OVERLAY_ICON_WIDTH, GUI_OVERLAY_ICON_HEIGHT, g_gui_overlay_icon);
		} else {
//TODO			util_jpeg_decode565_littlefs("/images/overlay/volume/speaker-mute.jpg", g_gui_overlay_icon, GUI_OVERLAY_ICON_WIDTH*GUI_OVERLAY_ICON_HEIGHT);
//TODO			for(int y=0; y<GUI_OVERLAY_ICON_HEIGHT; y++) {
//TODO				for(int x=0; x<GUI_OVERLAY_ICON_WIDTH; x++) {
//TODO					if(g_gui_overlay_icon[y*GUI_OVERLAY_ICON_WIDTH+x] != TFT_BLACK) {
//TODO						g_gui_overlay.drawPixel(x, y, TFT_WHITE);
//TODO					}
//TODO				}
//TODO			}
		}
	}
}

