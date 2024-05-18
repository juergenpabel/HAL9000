#include <FS.h>
#include <TFT_eSPI.h>

#include "gui/overlay/overlay.h"
#include "util/jpeg.h"
#include "globals.h"


static int hal9000_frame(JPEGDRAW *pDraw) {
	for(int y=0; y<pDraw->iHeight; y++) {
		memcpy(&g_gui_buffer[(pDraw->y+y)*GUI_SCREEN_WIDTH+pDraw->x], &pDraw->pPixels[y*pDraw->iWidth+0], pDraw->iWidth*sizeof(uint16_t));
	}
	return true;
}


void gui_screen_hal9000_frame_draw(uint8_t* jpeg_data, uint32_t jpeg_size) {
	util_jpeg_decode565_ram(jpeg_data, jpeg_size, nullptr, 0, hal9000_frame);
	for(int y=0; y<GUI_SCREEN_HEIGHT/2; y++) {
		for(int x=0; x<GUI_SCREEN_WIDTH/2; x++) {
			g_gui_buffer[(y*GUI_SCREEN_WIDTH)+(GUI_SCREEN_WIDTH-x-1)] = g_gui_buffer[(y*GUI_SCREEN_WIDTH)+(x)];
		}
		memcpy(&g_gui_buffer[(GUI_SCREEN_HEIGHT-y-1)*(GUI_SCREEN_WIDTH)], &g_gui_buffer[(y)*(GUI_SCREEN_WIDTH)], GUI_SCREEN_WIDTH*sizeof(uint16_t));
	}
	for(int y=0; y<GUI_SCREEN_HEIGHT; y++) {
		for(int x=0; x<GUI_SCREEN_WIDTH; x++) {
			if(g_gui_overlay.readPixel(x,y) == TFT_WHITE) {
				g_gui_buffer[(y*GUI_SCREEN_WIDTH)+x] = TFT_WHITE;
			}
		}
	}
	g_gui.pushImage((TFT_WIDTH-GUI_SCREEN_WIDTH)/2, (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2, GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT, (uint16_t*)g_gui_buffer);
}

