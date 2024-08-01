#include <etl/string.h>

#include "gui/gui.h"

typedef etl::string<GLOBAL_KEY_SIZE>   gui_overlay_name;
typedef gui_refresh_t                (*gui_overlay_func)(bool refresh);

gui_overlay_func gui_overlay_get();
gui_overlay_func gui_overlay_set(const gui_overlay_name& overlay_name, gui_overlay_func overlay_func, bool overlay_refresh=true);

void          gui_overlay_set_refresh();
gui_refresh_t gui_overlay_update(bool refresh);

gui_refresh_t gui_overlay_off(bool refresh);
gui_refresh_t gui_overlay_on(bool refresh);
gui_refresh_t gui_overlay_none(bool refresh);
gui_refresh_t gui_overlay_volume(bool refresh);
gui_refresh_t gui_overlay_message(bool refresh);

