#include <PNGdec.h>
#include <SimpleWebSerial.h>
#include "gui/screen/splash/png.h"
#include "gui/util/png.h"
#include "globals.h"



static void draw2tft(PNGDRAW *pDraw) {
	uint16_t  pixels[TFT_WIDTH] = {0};

	g_gui_png.getLineAsRGB565(pDraw, pixels, PNG_RGB565_BIG_ENDIAN, 0xffffffff);
	g_gui_tft.pushRect(0, pDraw->y, pDraw->iWidth, 1, pixels);
}


void splash_png(const char* filename) {
	png_load_littlefs(filename, TFT_WIDTH, TFT_HEIGHT, NULL, draw2tft);
}

