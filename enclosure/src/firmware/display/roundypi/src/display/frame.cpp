#include "globals.h"

#include <pngle.h>
#include <SimpleWebSerial.h>

static pngle_t* g_pngle = pngle_new();
static uint16_t g_image_565[TFT_WIDTH][TFT_HEIGHT] = {0};


void pngle_on_draw(pngle_t *pngle, uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint8_t rgba[4]) {
	uint16_t pixel565 = 0;
	uint8_t* frame_png = NULL;

	pixel565 = g_tft.color565(rgba[0], rgba[1], rgba[2]);
	pixel565 = pixel565 >> 8 | pixel565 << 8;

	g_image_565[  0 + y][  0 + x] = pixel565;
	g_image_565[239 - x][  0 + y] = pixel565;
	g_image_565[239 - y][239 - x] = pixel565;
	g_image_565[  0 + x][239 - y] = pixel565;
}


void frame_png_draw(uint8_t* png, uint16_t png_size) {
	pngle_reset(g_pngle);
	pngle_set_draw_callback(g_pngle, pngle_on_draw);
	if(pngle_feed(g_pngle, png, png_size) != png_size) {
		g_webserial.warn("pngle_feed() failed");
		pngle_reset(g_pngle);
		return;
	}
	g_tft.pushImage(0, 0, TFT_WIDTH, TFT_HEIGHT, (uint16_t*)g_image_565);
}

