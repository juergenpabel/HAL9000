#include <etl/string.h>

typedef etl::string<GLOBAL_KEY_SIZE>   gui_overlay_name;
typedef void                         (*gui_overlay_func)(bool refresh);

gui_overlay_func gui_overlay_get();
gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func);

void gui_overlay_update(bool refresh);

void gui_overlay_none(bool refresh);
void gui_overlay_volume(bool refresh);
void gui_overlay_message(bool refresh);

