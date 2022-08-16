#include <SimpleWebSerial.h>
#include <TFT_eSPI.h>
#include "gui/overlay/overlay.h"
#include "globals.h"

static uint16_t g_image_565[TFT_HEIGHT/2][TFT_WIDTH] = {0};


void screen_hal9000_frame_draw(uint8_t* jpeg_data, uint16_t jpeg_size) {
}

