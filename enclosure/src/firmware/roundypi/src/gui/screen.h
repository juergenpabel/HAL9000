typedef void (*screen_update_func)(bool refresh);

void screen_frames_load(const char* name);
screen_update_func screen_update(screen_update_func, bool force_refresh);
void screen_update_idle(bool force_refresh);
void screen_update_noop(bool force_refresh);
