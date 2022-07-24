#include "globals.h"
#include <hardware/watchdog.h>
#include <pico/bootrom.h>

void system_reset(int delay_ms) {
	watchdog_reboot(0, 0, delay_ms);
}


void system_flash(int delay_ms) {
	delay(delay_ms);
	reset_usb_boot(0, 0);
}

