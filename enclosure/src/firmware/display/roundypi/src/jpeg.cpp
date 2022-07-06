#include "defines.h"
#include "types.h"
#include "globals.h"

//include <FS.h>
//include <SdFat.h>
#include <JPEGDEC.h>
#include <SimpleWebSerial.h>


int draw_jpeg(JPEGDRAW *pDraw) {
	g_tft.pushRect(pDraw->x, pDraw->y, pDraw->iWidth, pDraw->iHeight, pDraw->pPixels);
	return 1;
}


void on_splash_jpeg(JSONVar parameter) {
	char     filename[256] = {0};
	File     file = {0};
	JPEGDEC  jpeg;

	snprintf(filename, sizeof(filename)-1, "%s/%s", "/images/splash", (const char*)parameter["filename"]);
	file = LittleFS.open(filename, "r");
	if(jpeg.open(file, draw_jpeg) < 0) {
		g_webserial.warn("show_splash_jpeg() -> jpeg.open() failed");
		return;
	}
	jpeg.setPixelType(RGB565_BIG_ENDIAN);
	jpeg.decode(120-jpeg.getWidth()/2, 120-jpeg.getHeight()/2, JPEG_AUTO_ROTATE);
	jpeg.close();
	file.close();
}
