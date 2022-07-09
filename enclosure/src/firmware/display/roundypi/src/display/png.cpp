#include "globals.h"

#include <PNGdec.h>
#include <SimpleWebSerial.h>
#include "png.h"


static void draw_png(PNGDRAW *pDraw) {
	uint16_t  pixels[TFT_WIDTH] = {0};
	PNG*      png = NULL;

	png = (PNG*)pDraw->pUser;
	if(png == NULL ) {
		//TODO:g_webserial.warn
	}
	png->getLineAsRGB565(pDraw, pixels, PNG_RGB565_BIG_ENDIAN, 0xffffffff);
	//g_tft.writeRect(0, pDraw->y + 24, pDraw->iWidth, 1, usPixels);
	//g_tft.pushRect(pDraw->x, pDraw->y, pDraw->iWidth, pDraw->iHeight, pDraw->pPixels);
}


static void* littlefs_open(const char *filename, int32_t *size) {
	File* file = NULL;

	file = new File();
	*file = LittleFS.open(filename, "r");
	*size = file->size();
	return file;
}


static int32_t littlefs_read(PNGFILE *handle, uint8_t *buffer, int32_t length) {
	return ((File*)handle->fHandle)->read(buffer, length);
}


static int32_t littlefs_seek(PNGFILE *handle, int32_t position) {
	return ((File*)handle->fHandle)->seek(position);
}


static void littlefs_close(void* handle) {
	File* file = NULL;

	file = (File*)handle;
	file->close();
	delete file;
}


void splash_png(const char* filename) {
	PNG   png;

	if(png.open(filename, littlefs_open, littlefs_close, littlefs_read, littlefs_seek, draw_png) < 0) {
		g_webserial.warn("splash_png() -> png.open() failed");
		return;
	}
	png.decode(&png, 0);
	png.close();
}

