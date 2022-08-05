typedef void (*overlay_update_func)();

overlay_update_func overlay_update(overlay_update_func);

void overlay_update_noop();
void overlay_update_volume();
void overlay_update_message();

