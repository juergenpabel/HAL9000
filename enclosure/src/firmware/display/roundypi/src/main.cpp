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
#include "display.h"
#include "jpeg.h"
#include "time.h"

extern "C" char* sbrk(int incr);
int freeRam() {
  char top;
  return &top - reinterpret_cast<char*>(sbrk(0));
}

TFT_eSPI        g_tft = TFT_eSPI();
SimpleWebSerial g_webserial;


sequence_t* g_sequence = NULL;
sequence_t  g_sequences_queue[SEQUENCES_MAX] = {0};
png_t       g_frames_png[FRAMES_PNG_MAX] = {0};
uint16_t    g_image_565[240][240] = {0};



void setup() {
	Serial.begin(115200);
	delay(1000);
	g_webserial.send("RoundyPI", "setup()");
	pinMode(TFT_BL, OUTPUT);
	digitalWrite(TFT_BL, LOW);

	g_tft.begin();
	//g_tft.setSwapBytes(true);
	g_tft.setRotation(2);
	g_tft.fillScreen(TFT_BLACK);
	g_tft.setTextColor(TFT_WHITE, TFT_BLACK);
	g_tft.setTextFont(1);
	g_tft.setTextDatum(4);
	g_tft.setTextSize(3);
	digitalWrite(TFT_BL, HIGH);
	g_tft.drawString("ready", 120, 120);
	g_webserial.send("RoundyPI", "TFT ready");

	if(!LittleFS.begin()) {
		g_webserial.warn("LittleFS error, halting");
		while(1) delay(1);
	}
	g_webserial.send("RoundyPI", "LittleFS ready");

	g_sequences_queue[0].type = 'Q';
	strncpy(g_sequences_queue[0].name, "init", sizeof(g_sequences_queue[0].name)-1);
	g_sequences_queue[0].timeout = 0;
	g_sequences_queue[0].next = NULL;
	g_sequence = &g_sequences_queue[0];
	g_webserial.send("RoundyPI", "Sequences ready");

	g_webserial.on("time:sync", on_time_sync);
	g_webserial.on("splash:jpeg", on_splash_jpeg);
	g_webserial.on("sequences", on_hal_sequences);
	g_webserial.on("sequence:timeout", on_hal_sequence_timeout);
	g_webserial.on("display:backlight", on_hal_display_backlight);
	g_webserial.send("RoundyPI", "Webserial ready");

	g_webserial.send("RoundyPI", "loop()");
	g_webserial.send("FreeRAM", String(freeRam(), DEC));
}


void loop() {
	static   time_t previously = 0;
	volatile time_t currently = now();

	draw_frames();
	g_webserial.check();
	delay(10);

	sequence_t* last_sequence = g_sequence;
	sequence_t* next_sequence = g_sequence->next;
	if(last_sequence->timeout > 0) {
		if(currently > last_sequence->timeout) {
			last_sequence->timeout = 0;
		}
	}
	if(last_sequence->timeout == 0) {
		if(next_sequence != NULL) {
			last_sequence->type = '\0';
			last_sequence->name[0] = '\0';
			last_sequence->timeout = 0;
			last_sequence->next = NULL;
			if(next_sequence->type == 'Q') {
				load_hal_frames(next_sequence->name);
			}
g_webserial.send("FreeRAM", String(freeRam(), DEC));
			g_sequence = next_sequence;
//			if(g_sequence->timeout > 0) {
				g_sequence->timeout += now();
//			}
		} else {
			if(minute(currently) != minute(previously)) {
				char clock[6] = {0};

				previously = currently;
				digitalWrite(TFT_BL, HIGH);
				snprintf(clock, sizeof(clock), "%02d:%02d", hour(currently), minute(currently));
				g_tft.drawString(clock, 120, 120);
			}
		}
	}
}

