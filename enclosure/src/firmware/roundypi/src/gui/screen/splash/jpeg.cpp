#include "globals.h"

#include <JPEGDEC.h>
#include <SimpleWebSerial.h>
#include "jpeg.h"


static int draw_jpeg(JPEGDRAW *pDraw) {
	g_tft.pushRect(pDraw->x, pDraw->y, pDraw->iWidth, pDraw->iHeight, pDraw->pPixels);
	return 1;
}


void splash_jpeg(const char* filename) {
	File     file = {0};
	JPEGDEC  jpeg;

	file = LittleFS.open(filename, "r");
	if(jpeg.open(file, draw_jpeg) < 0) {
		g_webserial.send("syslog", "show_splash_jpeg() -> jpeg.open() failed");
		return;
	}
	jpeg.setPixelType(RGB565_BIG_ENDIAN);
	jpeg.decode(120-jpeg.getWidth()/2, 120-jpeg.getHeight()/2, JPEG_AUTO_ROTATE);
	jpeg.close();
	file.close();
}
