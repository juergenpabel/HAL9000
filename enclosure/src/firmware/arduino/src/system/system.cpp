#include <FS.h>
#include <LittleFS.h>
#include <TimeLib.h>

#include "system/system.h"
#include "device/microcontroller/include.h"
#include "globals.h"


void System::start() {
	bool  booting = true;

	g_device_board.start(booting);
	if(booting == true) {
		g_application.setStatus(StatusBooting);
		g_util_webserial.send("syslog/debug", "system was powered on (booting, provisioning)");
	} else {
		g_application.setStatus(StatusConfiguring);
		g_util_webserial.send("syslog/debug", "system was resetted (not booting, configuring)");
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


void System::configure() {
	static etl::string<GLOBAL_FILENAME_SIZE> filename;
	static StaticJsonDocument<APPLICATION_JSON_FILESIZE_MAX*2> json;
	       File file;

	filename  = "/system/board/";
	filename += g_device_board.getIdentifier();
	filename += "/configuration.json";
	if(LittleFS.exists(filename.c_str()) == true) {
		file = LittleFS.open(filename.c_str(), "r");
		if(deserializeJson(json, file) != DeserializationError::Ok) {
			file.close();
			return;
		}
		file.close();
		if(g_device_board.configure(json.as<JsonVariant>()) == false) {
			return;
		}
	}
}


void System::reset() {
	bool      host_rebooting = false;

	if(g_application.getStatus() == StatusRebooting) {
		host_rebooting = true;
	}
	g_device_board.reset(host_rebooting);
	//this codepath should never be taken 
	g_device_board.displayOn();
	g_gui.fillScreen(TFT_BLACK);
	g_gui.drawString("ERROR resetting", (TFT_WIDTH-GUI_SCREEN_WIDTH)/2+(GUI_SCREEN_WIDTH/2), (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/2));
	g_device_board.displayOn();
	while(true) {
		delay(1);
	}
}


void System::halt() {
	g_device_board.halt();
	//this codepath should never be taken 
	g_device_board.displayOn();
	g_gui.fillScreen(TFT_BLACK);
	g_gui.drawString("ERROR halting", (TFT_WIDTH-GUI_SCREEN_WIDTH)/2+(GUI_SCREEN_WIDTH/2), (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/2));
	g_device_board.displayOn();
	while(true) {
		delay(1);
	}
}

