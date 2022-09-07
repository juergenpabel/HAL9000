#include "gui/screen/screen.h"
#include "system/rp2040.h"
#include "util/jpeg.h"
#include "globals.h"


static const char*   g_startup_folder[] = {"startup/countdown", "startup/fadeout", NULL};
static int           g_startup_count[]  = {23, 19, 0};
static int           g_startup_delay[]  = {900, 100, 0};

static const char*   g_shutdown_folder[] = {"shutdown/monitor", "shutdown/fadeout", NULL};
static int           g_shutdown_count[]  = {80, 10, 0};
static int           g_shutdown_delay[]  = {25, 10, 0};

static const char**  g_animation_folder = NULL;
static int*          g_animation_count = NULL;
static int*          g_animation_delay = NULL;

static int           g_animation_nr = 0;
static int           g_animation_frame = 0;


static void gui_screen_animations(bool refresh) {
	if(g_animation_folder == NULL || g_animation_count == NULL || g_animation_delay == NULL) {
		return;
	}
	if(g_animation_frame == g_animation_count[g_animation_nr]) {
		g_animation_frame = 0;
		g_animation_nr++;
		if(g_animation_folder[g_animation_nr] == NULL || g_animation_count[g_animation_nr] == 0) {
			gui_screen_set(gui_screen_none);
			g_animation_folder = NULL;
			g_animation_count = NULL;
			g_animation_delay = NULL;
			return;
		}
	}
	if(refresh == true) {
		char filename[256];

		snprintf(filename, sizeof(filename), "/images/animations/%s/%02d.jpg", g_animation_folder[g_animation_nr], g_animation_frame);
		util_jpeg_decode565_littlefs(filename, g_gui_tft_buffer, TFT_WIDTH*TFT_HEIGHT);
		g_gui_tft.pushImage(0, 0, TFT_WIDTH, TFT_HEIGHT, (uint16_t*)g_gui_tft_buffer);
	}
	sleep_ms(g_animation_delay[g_animation_nr]);
	g_animation_frame++;
}


void gui_screen_animation_startup(bool refresh) {
	if(g_animation_folder == NULL || g_animation_count == NULL || g_animation_delay == NULL) {
		g_animation_folder = g_startup_folder;
		g_animation_count = g_startup_count;
		g_animation_delay = g_startup_delay;
		g_animation_nr = 0;
		g_animation_frame = 0;
	}
	gui_screen_animations(refresh);
}


void gui_screen_animation_shutdown(bool refresh) {
	if(g_animation_folder == NULL || g_animation_count == NULL || g_animation_delay == NULL) {
		g_animation_folder = g_shutdown_folder;
		g_animation_count = g_shutdown_count;
		g_animation_delay = g_shutdown_delay;
		g_animation_nr = 0;
		g_animation_frame = 0;
	}
	gui_screen_animations(refresh);
	if(gui_screen_get() == gui_screen_none) {
		system_rp2040_halt();
	}
}

