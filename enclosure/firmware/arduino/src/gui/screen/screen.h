#include <etl/string.h>
#include <TFT_eSPI.h>

#include "gui/gui.h"

typedef etl::string<GLOBAL_VALUE_SIZE>  gui_screen_name;
typedef unsigned long                 (*gui_screen_func)(unsigned long validity, TFT_eSPI* gui);

const gui_screen_name& gui_screen_getname();
gui_screen_func gui_screen_get();
gui_screen_func gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func);

void          gui_screen_set_refresh();
unsigned long gui_screen_update(unsigned long validity, TFT_eSPI* gui);

unsigned long gui_screen_off(unsigned long validity, TFT_eSPI* gui);
unsigned long gui_screen_on(unsigned long validity, TFT_eSPI* gui);
unsigned long gui_screen_none(unsigned long validity, TFT_eSPI* gui);

