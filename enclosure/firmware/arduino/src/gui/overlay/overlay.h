#include <etl/string.h>
#include <TFT_eSPI.h>

#include "gui/gui.h"


typedef etl::string<GLOBAL_KEY_SIZE>   gui_overlay_name;
typedef unsigned long                (*gui_overlay_func)(unsigned long lastDraw, TFT_eSPI* gui);

gui_overlay_func gui_overlay_get();
gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func);

void          gui_overlay_set_refresh();
unsigned long gui_overlay_update(unsigned long lastDraw, TFT_eSPI* gui);

unsigned long gui_overlay_off(unsigned long lastDraw, TFT_eSPI* gui);
unsigned long gui_overlay_on(unsigned long lastDraw, TFT_eSPI* gui);
unsigned long gui_overlay_none(unsigned long lastDraw, TFT_eSPI* gui);
unsigned long gui_overlay_volume(unsigned long lastDraw, TFT_eSPI* gui);
unsigned long gui_overlay_message(unsigned long lastDraw, TFT_eSPI* gui);

