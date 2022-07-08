#include "defines.h"
#include <TFT_eSPI.h>
#include <SimpleWebSerial.h>


extern TFT_eSPI        g_tft;
extern SimpleWebSerial g_webserial;

extern sequence_t* g_current_sequence;
extern sequence_t  g_sequences_queue[];
extern png_t       g_frames_png[];
extern uint16_t    g_image_565[240][240];

