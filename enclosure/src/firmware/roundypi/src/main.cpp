#include <TimeLib.h>
#include <TFT_eSPI.h>
#include <LittleFS.h>
#include <pngle.h>
#include <SPI.h>
#include <FS.h>
//include <SdFat.h>
#include <SimpleWebSerial.h>

#include "globals.h"
#include "system/webserial.h"
#include "filesystem/webserial.h"
#include "display/webserial.h"
#include "gui/webserial.h"
#include "system/system.h"
#include "gui/gui.h"
#include "gui/jpeg.h"


extern "C" char* sbrk(int incr);
int freeRam() {
  char top;
  return &top - reinterpret_cast<char*>(sbrk(0));
}

TFT_eSPI        g_tft = TFT_eSPI();
SimpleWebSerial g_webserial;


void setup() {
	Serial.begin(115200);
	g_tft.begin();
	g_tft.setRotation(2);
	g_tft.fillScreen(TFT_BLACK);
	g_tft.setTextColor(TFT_WHITE, TFT_BLACK);
	g_tft.setTextFont(1);
	g_tft.setTextDatum(4);
	g_tft.setTextSize(3);
	pinMode(TFT_BL, OUTPUT);
	digitalWrite(TFT_BL, LOW);

	if(!LittleFS.begin()) {
		while(1) {
			g_webserial.warn("LittleFS error, halting");
			delay(1000);
		}
	}

	delay(1000);
	if(!Serial) {
		splash_jpeg("/images/splash/error.jpg");
		digitalWrite(TFT_BL, HIGH);
		while(!Serial) {
			delay(1);
		}
		g_tft.fillScreen(TFT_BLACK);
		digitalWrite(TFT_BL, LOW);
	}
	digitalWrite(TFT_BL, HIGH);
	g_webserial.send("RoundyPI", "setup()");
	g_webserial.on("system:reset", on_system_reset);
	g_webserial.on("system:flash", on_system_flash);
	g_webserial.on("system:config", on_system_config);
	g_webserial.on("system:time", on_system_time);
	g_webserial.on("filesystem:flash", on_filesystem_flash);
	g_webserial.on("filesystem:sdcard", on_filesystem_sdcard);
	g_webserial.on("display:backlight", on_display_backlight);
	g_webserial.on("gui:sequence", on_gui_sequence);
	g_webserial.on("gui:splash", on_gui_splash);
	g_webserial.send("RoundyPI", "Webserial ready");
	delay(10);
	g_webserial.send("RoundyPI", "loop()");
	//g_webserial.send("FreeRAM", String(freeRam(), DEC));
}


void loop() {
	if(!Serial) {
		system_reset(0);
	}
	g_webserial.check();
	gui_update(NULL);
	delay(10);
}

