#include <TimeLib.h>
#include <hardware/watchdog.h>
#include <pico/bootrom.h>
#include <pico/multicore.h>
#include "globals.h"


static volatile long g_sync_epoch_secs = 0;


void rp2040_reset() {
	multicore_reset_core1();
	watchdog_reboot(0, 0, 0);
}


void rp2040_reset_uf2() {
	multicore_reset_core1();
	reset_usb_boot(0, 0);
}


time_t rp2040_time_sync() {
        uint32_t timeout;

        g_sync_epoch_secs = 0;
        g_webserial.sendEvent("system:time");
        timeout = millis() + 1000;
        while(g_sync_epoch_secs == 0 && millis() < timeout) {
                g_webserial.check();
                sleep_ms(10);
        }
        return g_sync_epoch_secs;
}


void rp2040_time_set(long epoch) {
	g_sync_epoch_secs = epoch;
}
