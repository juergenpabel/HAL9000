#include <etl/string.h>
#include <TFT_eSPI.h>

#include "gui/gui.h"

typedef etl::string<GLOBAL_KEY_SIZE>   gui_screen_name;
typedef unsigned long                (*gui_screen_func)(unsigned long lastDraw, TFT_eSPI* gui);

gui_screen_func gui_screen_get();
gui_screen_func gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func);

void          gui_screen_set_refresh();
unsigned long gui_screen_update(unsigned long lastDraw, TFT_eSPI* gui);

unsigned long gui_screen_off(unsigned long lastDraw, TFT_eSPI* gui);
unsigned long gui_screen_on(unsigned long lastDraw, TFT_eSPI* gui);
unsigned long gui_screen_none(unsigned long lastDraw, TFT_eSPI* gui);

