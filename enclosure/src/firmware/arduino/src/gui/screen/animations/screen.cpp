#include "gui/screen/screen.h"
#include "system/system.h"
#include "util/jpeg.h"
#include "globals.h"


static const char*   g_startup_folder[] = {"startup/countdown", "startup/fadeout", nullptr};
static int           g_startup_count[]  = {23, 19, 0};
static int           g_startup_delay[]  = {900, 100, 0};

static const char*   g_shutdown_folder[] = {"shutdown", nullptr};
static int           g_shutdown_count[]  = {70, 0};
static int           g_shutdown_delay[]  = {0, 0};

static const char**  g_animation_folder = nullptr;
static int*          g_animation_count = nullptr;
static int*          g_animation_delay = nullptr;

static int           g_animation_nr = 0;
static int           g_animation_frame = 0;


static void gui_screen_animations(bool refresh) {
	if(g_animation_folder == nullptr || g_animation_count == nullptr || g_animation_delay == nullptr) {
		return;
	}
	if(g_animation_frame == g_animation_count[g_animation_nr]) {
		g_animation_frame = 0;
		g_animation_nr++;
		if(g_animation_folder[g_animation_nr] == nullptr || g_animation_count[g_animation_nr] == 0) {
			gui_screen_set(gui_screen_none);
			g_animation_folder = nullptr;
			g_animation_count = nullptr;
			g_animation_delay = nullptr;
			return;
		}
	}
	if(refresh == true) {
		char filename[256];

		snprintf(filename, sizeof(filename), "/images/animations/%s/%02d.jpg", g_animation_folder[g_animation_nr], g_animation_frame);
		util_jpeg_decode565_littlefs(filename, g_gui_buffer, TFT_WIDTH*TFT_HEIGHT);
		g_gui.pushImage(0, 0, TFT_WIDTH, TFT_HEIGHT, (uint16_t*)g_gui_buffer);
	}
	delay(g_animation_delay[g_animation_nr]);
	g_animation_frame++;
}


void gui_screen_animation_startup(bool refresh) {
	if(g_animation_folder == nullptr || g_animation_count == nullptr || g_animation_delay == nullptr) {
		g_animation_folder = g_startup_folder;
		g_animation_count = g_startup_count;
		g_animation_delay = g_startup_delay;
		g_animation_nr = 0;
		g_animation_frame = 0;
	}
	gui_screen_animations(refresh);
}


void gui_screen_animation_shutdown(bool refresh) {
	if(g_animation_folder == nullptr || g_animation_count == nullptr || g_animation_delay == nullptr) {
		g_animation_folder = g_shutdown_folder;
		g_animation_count = g_shutdown_count;
		g_animation_delay = g_shutdown_delay;
		g_animation_nr = 0;
		g_animation_frame = 0;
	}
	gui_screen_animations(refresh);
}

