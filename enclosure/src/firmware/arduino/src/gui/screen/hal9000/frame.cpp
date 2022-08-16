#include <SimpleWebSerial.h>
#include <TFT_eSPI.h>
#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


static int hal9000_frame(JPEGDRAW *pDraw) {
	uint16_t*  image565_data;

	for(int y=0; y<pDraw->iHeight; y++) {
		memcpy(&g_gui_tft_buffer[y*TFT_WIDTH+0], &pDraw->pPixels[y*pDraw->iWidth+0], pDraw->iWidth*sizeof(uint16_t));
	}
	return true;
}


void gui_screen_hal9000_frame_draw(uint8_t* jpeg_data, uint32_t jpeg_size) {
	util_jpeg_decode565_ram(jpeg_data, jpeg_size, NULL, 0, hal9000_frame);
	for(int y=0; y<TFT_HEIGHT/2; y++) {
		for(int x=0; x<TFT_WIDTH/2; x++) {
			g_gui_tft_buffer[(y*TFT_WIDTH)+(TFT_WIDTH-x-1)] = g_gui_tft_buffer[(y*TFT_WIDTH)+(x)];
		}
		memcpy(&g_gui_tft_buffer[(TFT_HEIGHT-y-1)*(TFT_WIDTH)], &g_gui_tft_buffer[(y)*(TFT_WIDTH)], TFT_WIDTH*sizeof(uint16_t));
	}
	g_gui_tft.pushImage(0, 0, TFT_WIDTH, TFT_HEIGHT, (uint16_t*)g_gui_tft_buffer);
}

