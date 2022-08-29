#include <TimeLib.h>


typedef void (*screen_func)(bool refresh);

screen_func screen_get();
screen_func screen_set(screen_func);
void        screen_set_refresh();
void screen_update(bool force_refresh);


void screen_idle(bool force_refresh);
void screen_menu(bool force_refresh);
void screen_hal9000(bool force_refresh);


extern time_t  g_gui_screen_idle_clock_previously;

