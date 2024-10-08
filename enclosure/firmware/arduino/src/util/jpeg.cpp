#include <FS.h>
#include <LittleFS.h>

#include "util/jpeg.h"
#include "globals.h"


static int render2buffer(JPEGDRAW *pDraw) {
	uint16_t*  image565_data;

	image565_data = (uint16_t*)pDraw->pUser;
	for(int line=0; line<pDraw->iHeight; line++) {
		memcpy(&image565_data[(pDraw->y+line)*(GUI_SCREEN_WIDTH)+(pDraw->x)], &pDraw->pPixels[(line)*(pDraw->iWidth)], sizeof(uint16_t)*(pDraw->iWidth));
	}
	return true;
}


void util_jpeg_decode565_littlefs(const etl::string<GLOBAL_FILENAME_SIZE>& filename, uint16_t* image565_data, uint32_t image565_size, JPEG_DRAW_CALLBACK* image565_func) {
	File  file;

	file = LittleFS.open(filename.c_str(), "r");
	if(static_cast<bool>(file) == false) {
		g_system_application.addErrorContext("util_jpeg_decode565_littlefs(): file not found: 'TODO:filename'");
		return;
	}
	if(image565_func == nullptr) {
		if(image565_data == nullptr || image565_size == 0) {
			g_system_application.addErrorContext("util_jpeg_decode565_littlefs(): JPEG_DRAW_CALLBACK must not be NULL");
			return;
		}
		image565_func = render2buffer;
	}
	if(g_util_jpeg.open(file, image565_func) == false) {
		g_system_application.addErrorContext("util_jpeg_decode565_littlefs(): g_util_jpeg.open() failed for 'TODO:filename'");
		return;
	}
	if(image565_data != nullptr && image565_size > 0) {
		if((g_util_jpeg.getWidth()*g_util_jpeg.getHeight()) > (int)image565_size) {
			g_system_application.addErrorContext("util_jpeg_decode565_littlefs(): provided buffer is too small (jpeg:width*height)");
			g_util_jpeg.close();
		}
	}
	g_util_jpeg.setPixelType(RGB565_BIG_ENDIAN);
	g_util_jpeg.setUserPointer(image565_data);
	g_util_jpeg.decode(0, 0, 0);
	g_util_jpeg.close();
}

