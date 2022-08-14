#include <SimpleWebSerial.h>
#include "gui/util/png.h"
#include "globals.h"


typedef struct {
	uint16_t  width;
	uint16_t  height;
	uint16_t* buffer;
	uint16_t  current_row;
} image_565_t;


static void draw2buffer(PNGDRAW *pDraw) {
	image_565_t* image = (image_565_t*)pDraw->pUser;

	g_gui_png.getLineAsRGB565(pDraw, &image->buffer[(image->width*2)*(image->current_row)], PNG_RGB565_BIG_ENDIAN, 0xffffffff);
	image->current_row++;
}


static void* littlefs_open(const char *filename, int32_t *size) {
	File*  file = NULL;

	file = new File();
	*file = LittleFS.open(filename, "r");
	if(*file == false) {
		g_util_webserial.send("syslog", "littlefs_open(): file not found");
		g_util_webserial.send("syslog", filename);
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
	File*  file = NULL;

	file = (File*)handle;
	file->close();
	delete file;
}


void png_load_littlefs(const char* filename, uint16_t width, uint16_t height, uint16_t* buffer, PNG_DRAW_CALLBACK* draw) {
	image_565_t  image;

	image.width = width;
	image.height = height;
	image.buffer = buffer;
	image.current_row = 0;
	if(draw == NULL) {
		draw = draw2buffer;
	}
	if(g_gui_png.open(filename, littlefs_open, littlefs_close, littlefs_read, littlefs_seek, draw) != PNG_SUCCESS) {
		g_util_webserial.send("syslog", "png_load_littlefs() -> g_gui_png.open() failed");
		return;
	}
	g_gui_png.decode(&image, 0);
	g_gui_png.close();
}

