#include <JPEGDEC.h>

void util_jpeg_decode565_ram(uint8_t* jpeg_data, uint32_t jpeg_size, uint16_t* image565_data, uint32_t image565_size, JPEG_DRAW_CALLBACK* image_func = NULL);
void util_jpeg_decode565_littlefs(const char* filename,              uint16_t* image565_data, uint32_t image565_size, JPEG_DRAW_CALLBACK* image_func = NULL);

