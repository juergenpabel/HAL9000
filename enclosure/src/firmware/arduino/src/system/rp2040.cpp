#include <TimeLib.h>
#include <JSONVar.h>
#include <hardware/watchdog.h>
#include <hardware/resets.h>
#include <pico/bootrom.h>
#include <pico/multicore.h>
#include "globals.h"


static volatile long g_sync_epoch_secs = 0;


void system_rp2040_start() {
	Serial.begin(115200);
	if((watchdog_hw)->scratch[0] == 0x00002001 && (watchdog_hw)->scratch[1] == 0x00009000) {
		g_sync_epoch_secs = (watchdog_hw)->scratch[2];
		setTime(g_sync_epoch_secs);
		(watchdog_hw)->scratch[0] = 0x00000000;
		(watchdog_hw)->scratch[1] = 0x00000000;
		(watchdog_hw)->scratch[2] = 0x00000000;
		g_util_webserial.send("system/rp2040", "recovered time from rp2040 scratch registers");
	}
	pinMode(TFT_BL, OUTPUT);
	digitalWrite(TFT_BL, HIGH);
	g_system_status["system/audio:volume/level"] = "50";
	g_system_status["system/audio:volume/mute"] = "False";
	g_system_status["system/state:conciousness"] = "awake";
}


void system_rp2040_reset() {
	if(g_system_settings.save("/system/configuration.bson") == false) {
		g_util_webserial.send("system/rp2040", "rp2040_reset(): settings could not be saved to flash/littlefs");
		g_util_webserial.send("system/rp2040", "rp2040_reset(): any modified settings will be lost");
	}
	multicore_reset_core1();

	reset_block(RESETS_RESET_SPI0_BITS | RESETS_RESET_SPI1_BITS);
	unreset_block_wait(RESETS_RESET_SPI0_BITS | RESETS_RESET_SPI1_BITS);

	reset_block(RESETS_RESET_I2C0_BITS | RESETS_RESET_I2C1_BITS);
	unreset_block_wait(RESETS_RESET_I2C0_BITS | RESETS_RESET_I2C1_BITS);

	reset_block(RESETS_RESET_IO_BANK0_BITS);
	unreset_block_wait(RESETS_RESET_IO_BANK0_BITS);

	reset_block(RESETS_RESET_USBCTRL_BITS);
	unreset_block_wait(RESETS_RESET_USBCTRL_BITS);
	if(year(g_sync_epoch_secs) >= 2001) {
		(watchdog_hw)->scratch[0] = 0x00002001;
		(watchdog_hw)->scratch[1] = 0x00009000;
		(watchdog_hw)->scratch[2] = now();
	}
	watchdog_reboot(0, SRAM_END, 0);
}


void system_rp2040_reset_uf2() {
	multicore_reset_core1();
	reset_usb_boot(0, 0);
}


void system_rp2040_set_epoch(long epoch) {
	g_sync_epoch_secs = epoch;
}


time_t system_rp2040_timelib_sync() {
	JSONVar  request;
	uint32_t timeout;

	g_sync_epoch_secs = 0;
	request["sync"] = JSONVar();
	request["sync"]["format"] = "epoch";

	g_util_webserial.send("system/time", request);
	timeout = millis() + 1000;
	while(g_sync_epoch_secs == 0 && millis() < timeout) {
		g_util_webserial.check();
		sleep_ms(100);
	}
	return g_sync_epoch_secs;
}

