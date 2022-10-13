#include <TimeLib.h>

#include "device/microcontroller/include.h"
#include "globals.h"


void system_start() {
	bool  host_booting = true;

	g_device_board.start(host_booting);
	if(host_booting == false) {
		g_system_runtime["system/state:app/target"] = "waiting";
		g_util_webserial.send("syslog/debug", "host system not booting");
	}
	if(host_booting == true) {
		g_device_board.displayOn();
	}
	g_gui_buffer = (uint16_t*)malloc(GUI_SCREEN_HEIGHT*GUI_SCREEN_WIDTH*sizeof(uint16_t));
	if(g_gui_buffer == nullptr) {
		while(true) {
			g_util_webserial.send("syslog/fatal", "g_gui_buffer could not be malloc()ed, halting");
			delay(1000);
		}
	}
	g_gui.begin();
	g_gui.setRotation(TFT_ORIENTATION_LOGICAL);
	g_gui.fillScreen(TFT_BLACK);
	g_gui.setTextColor(TFT_WHITE);
	g_gui.setTextFont(1);
	g_gui.setTextSize(5);
	g_gui.setTextDatum(MC_DATUM);
	g_gui_overlay.setColorDepth(1);
	g_gui_overlay.setBitmapColor(TFT_WHITE, TFT_BLACK);
	g_gui_overlay.createSprite(GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT);
	g_gui_overlay.setTextColor(TFT_WHITE, TFT_BLACK, false);
	g_gui_overlay.setTextFont(1);
	g_gui_overlay.setTextSize(2);
	g_gui_overlay.setTextDatum(MC_DATUM);
}


void system_reset() {
	uint32_t  epoch = 0;
	bool      host_rebooting = false;

	if(year() > 2001) {
		epoch = now();
	}
	if(g_system_runtime["system/state:app/target"].compare("rebooting") == 0) {
		host_rebooting = true;
	}
	g_device_board.displayOff();
	g_device_board.reset(epoch, host_rebooting);
	//this codepath should never be taken 
	g_gui.fillScreen(TFT_BLACK);
	g_gui.drawString("ERROR, halting.", (TFT_WIDTH-GUI_SCREEN_WIDTH)/2+(GUI_SCREEN_WIDTH/2), (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/2));
	g_device_board.displayOn();
	while(true) {
		delay(1);
	}
}


void system_halt() {
	g_device_board.displayOff();
	g_device_board.halt();
	while(true) {
		delay(1);
	}
}

