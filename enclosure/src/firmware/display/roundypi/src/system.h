#include <JSONVar.h>

time_t time_sync();
void on_system_time(JSONVar parameter);
void on_system_reset(JSONVar parameter);
void on_system_flash(JSONVar parameter);

void system_reset(int delay_ms);
void system_flash(int delay_ms);

