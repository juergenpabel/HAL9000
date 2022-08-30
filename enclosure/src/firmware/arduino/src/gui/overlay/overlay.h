typedef void (*gui_overlay_func)(bool force_refresh);

gui_overlay_func gui_overlay_get();
gui_overlay_func gui_overlay_set(gui_overlay_func);

void gui_overlay_update(bool force_refresh);

void gui_overlay_none(bool force_refresh);
void gui_overlay_volume(bool force_refresh);
void gui_overlay_message(bool force_refresh);

