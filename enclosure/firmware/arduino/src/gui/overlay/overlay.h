#include <etl/string.h>

typedef etl::string<GLOBAL_KEY_SIZE>   gui_overlay_name;
typedef bool                         (*gui_overlay_func)(bool refresh);

gui_overlay_func gui_overlay_get();
gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func);

void gui_overlay_set_refresh();
bool gui_overlay_update(bool refresh);

bool gui_overlay_none(bool refresh);
bool gui_overlay_volume(bool refresh);
bool gui_overlay_message(bool refresh);

