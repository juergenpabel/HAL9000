typedef void (*overlay_func)(bool force_refresh);

overlay_func overlay_get();
overlay_func overlay_set(overlay_func);

void overlay_update(bool force_refresh);

void overlay_none(bool force_refresh);
void overlay_menu(bool force_refresh);
void overlay_volume(bool force_refresh);
void overlay_message(bool force_refresh);

