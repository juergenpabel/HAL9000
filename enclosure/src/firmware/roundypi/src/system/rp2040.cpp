#include <TimeLib.h>
#include <JSONVar.h>
#include <hardware/watchdog.h>
#include <hardware/resets.h>
#include <pico/bootrom.h>
#include <pico/multicore.h>
#include "globals.h"


static volatile long g_sync_epoch_secs = 0;


void rp2040_reset() {
	multicore_reset_core1();

	reset_block(RESETS_RESET_SPI0_BITS | RESETS_RESET_SPI1_BITS);
	unreset_block_wait(RESETS_RESET_SPI0_BITS | RESETS_RESET_SPI1_BITS);

	reset_block(RESETS_RESET_I2C0_BITS | RESETS_RESET_I2C1_BITS);
	unreset_block_wait(RESETS_RESET_I2C0_BITS | RESETS_RESET_I2C1_BITS);

	reset_block(RESETS_RESET_IO_BANK0_BITS);
	unreset_block_wait(RESETS_RESET_IO_BANK0_BITS);

	reset_block(RESETS_RESET_USBCTRL_BITS);
	unreset_block_wait(RESETS_RESET_USBCTRL_BITS);

	watchdog_reboot(0, SRAM_END, 0);
}


void rp2040_reset_uf2() {
	multicore_reset_core1();
	reset_usb_boot(0, 0);
}


void rp2040_time_sync(long epoch) {
	g_sync_epoch_secs = epoch;
}


time_t rp2040_timelib_sync() {
	JSONVar  request;
        uint32_t timeout;

        g_sync_epoch_secs = 0;
	request["sync"] = JSONVar();
	request["sync"]["format"] = "epoch";

	g_webserial.send("system/time#sync", request);
        timeout = millis() + 1000;
        while(g_sync_epoch_secs == 0 && millis() < timeout) {
                g_webserial.check();
                sleep_ms(10);
        }
        return g_sync_epoch_secs;
}

