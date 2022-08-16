#include "globals.h"

#include <JPEGDEC.h>
#include <SimpleWebSerial.h>
#include "gui/screen/splash/jpeg.h"


static int draw_jpeg(JPEGDRAW *pDraw) {
	g_gui_tft.pushRect(pDraw->x, pDraw->y, pDraw->iWidth, pDraw->iHeight, pDraw->pPixels);
	return 1;
}


void splash_jpeg(const char* filename) {
	File     file = {0};

	file = LittleFS.open(filename, "r");
	if(g_gui_jpeg.open(file, draw_jpeg) < 0) {
		g_util_webserial.send("syslog", "show_splash_jpeg() -> jpeg.open() failed");
		return;
	}
	g_gui_jpeg.setPixelType(RGB565_BIG_ENDIAN);
	g_gui_jpeg.decode(120-g_gui_jpeg.getWidth()/2, 120-g_gui_jpeg.getHeight()/2, JPEG_AUTO_ROTATE);
	g_gui_jpeg.close();
	file.close();
}
