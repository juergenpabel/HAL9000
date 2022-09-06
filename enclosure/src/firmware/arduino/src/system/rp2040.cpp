#include <TimeLib.h>
#include <JSONVar.h>
#include <hardware/watchdog.h>
#include <hardware/structs/watchdog.h>
#include <hardware/resets.h>
#include <pico/bootrom.h>
#include <pico/multicore.h>
#include "globals.h"


void system_rp2040_start() {
	Serial.begin(115200);
//TODO	if((watchdog_hw->scratch[5] == 0x00002001) && (watchdog_hw->scratch[6] == 0x00009000)) {
//TODO		g_sync_epoch_secs = watchdog_hw->scratch[7];
//TODO		setTime(g_sync_epoch_secs);
//TODO		watchdog_hw->scratch[5] = 0x00000000;
//TODO		watchdog_hw->scratch[6] = 0x00000000;
//TODO		watchdog_hw->scratch[7] = 0x00000000;
//TODO		g_util_webserial_queue.pushMessage("syslog", "recovered time from rp2040 scratch registers");
//TODO	}
	pinMode(TFT_BL, OUTPUT);
	digitalWrite(TFT_BL, HIGH);
}


void system_rp2040_reset() {
//TODO	if(year(g_sync_epoch_secs) >= 2001) {
//TODO		watchdog_hw->scratch[5] = 0x00002001;
//TODO		watchdog_hw->scratch[6] = 0x00009000;
//TODO		watchdog_hw->scratch[7] = now();
//TODO	}
	digitalWrite(TFT_BL, LOW);
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
	reset_usb_boot(0, 0);
	while(true) {
		sleep_ms(1);
	}
}


void system_rp2040_reset_uf2() {
	multicore_reset_core1();
	reset_usb_boot(0, 0);
	while(true) {
		sleep_ms(1);
	}
}


void system_rp2040_halt() {
	multicore_reset_core1();
	digitalWrite(TFT_BL, LOW);
	Serial.end();
	while(true) {
		sleep_ms(1);
	}
}

