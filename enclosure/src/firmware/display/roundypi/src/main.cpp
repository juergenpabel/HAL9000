#include "defines.h"
#include <TimeLib.h>
#include <TFT_eSPI.h>
#include <LittleFS.h>
#include <pngle.h>
#include <SPI.h>
#include <FS.h>
//include <SdFat.h>
#include <SimpleWebSerial.h>

#include "types.h"
#include "globals.h"
#include "display.h"
#include "jpeg.h"
#include "system.h"

extern "C" char* sbrk(int incr);
int freeRam() {
  char top;
  return &top - reinterpret_cast<char*>(sbrk(0));
}

TFT_eSPI        g_tft = TFT_eSPI();
SimpleWebSerial g_webserial;


sequence_t* g_current_sequence = &g_sequences_queue[0];
sequence_t  g_sequences_queue[SEQUENCES_MAX] = {0};
png_t       g_frames_png[FRAMES_PNG_MAX] = {0};
uint16_t    g_image_565[240][240] = {0};



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
	g_webserial.send("RoundyPI", "setup()");
	digitalWrite(TFT_BL, HIGH);
	for(int i=0; i<SEQUENCES_MAX; i++) {
		g_sequences_queue[i].next = &g_sequences_queue[i];
	}
	g_webserial.on("system:reset", on_system_reset);
	g_webserial.on("system:flash", on_system_flash);
	g_webserial.on("system:time", on_system_time);
	g_webserial.on("display:backlight", on_display_backlight);
	g_webserial.on("display:sequence", on_display_sequence);
	g_webserial.on("display:splash", on_display_splash);
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
	display_show();
	if(g_current_sequence->name[0] != '\0') {
		if(g_current_sequence->timeout > 0) {
			time_t currently = now();

			if(currently > g_current_sequence->timeout) {
				g_current_sequence->timeout = 0;
			}
		}
		if(g_current_sequence->timeout == 0) {
			g_current_sequence->name[0] = '\0';
			if(g_current_sequence->next != g_current_sequence) {
				g_current_sequence = g_current_sequence->next;
				display_frames_load(g_current_sequence->name);
				if(g_current_sequence->timeout > 0) {
					g_current_sequence->timeout += now();
				}
			} else {
				g_tft.fillScreen(TFT_BLACK);
			}
		}
	}
	delay(10);
}

