#include "globals.h"

#include <PNGdec.h>
#include <SimpleWebSerial.h>
#include "png.h"


static void draw_png(PNGDRAW *pDraw) {
	uint16_t  pixels[TFT_WIDTH] = {0};
	PNG*      png = NULL;

	png = (PNG*)pDraw->pUser;
	if(png == NULL ) {
		g_webserial.warn("draw_png(): no png handle");
		return;
	}
	png->getLineAsRGB565(pDraw, pixels, PNG_RGB565_BIG_ENDIAN, 0xffffffff);
	g_tft.pushRect(0, pDraw->y, pDraw->iWidth, 1, pixels);
}


static void* littlefs_open(const char *filename, int32_t *size) {
	File* file = NULL;

	file = new File();
	*file = LittleFS.open(filename, "r");
	if(*file == false) {
		g_webserial.warn("littlefs_open(): file not found");
		g_webserial.warn(filename);
		return NULL;
	}
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
	static PNG png; //static because of stack memory pressure

	if(png.open(filename, littlefs_open, littlefs_close, littlefs_read, littlefs_seek, draw_png) != PNG_SUCCESS) {
		g_webserial.warn("splash_png() -> png.open() failed");
		return;
	}
	png.decode(&png, 0);
	png.close();
}

