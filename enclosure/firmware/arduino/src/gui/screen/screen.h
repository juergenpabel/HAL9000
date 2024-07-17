#include <etl/string.h>

typedef etl::string<GLOBAL_KEY_SIZE>   gui_screen_name;
typedef void                         (*gui_screen_func)(bool refresh);

gui_screen_func gui_screen_get();
void            gui_screen_set(const gui_screen_name& screen_name, gui_screen_func screen_func);
void            gui_screen_set_refresh();

void gui_screen_update(bool refresh);
void gui_screen_none(bool refresh);

