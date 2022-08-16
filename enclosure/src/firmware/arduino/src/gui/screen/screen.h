typedef void (*screen_func)(bool refresh);

screen_func screen_get();
screen_func screen_set(screen_func);

void screen_update(bool force_refresh);

void screen_idle(bool force_refresh);

