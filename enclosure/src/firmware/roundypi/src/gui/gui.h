typedef void (*gui_update_func)();

void gui_frames_load(const char* name);
gui_update_func gui_update(gui_update_func);
void gui_update_idle();
