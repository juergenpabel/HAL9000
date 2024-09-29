#include "gui/screen/screen.h"
#include "gui/screen/animations/screen.h"
#include "globals.h"


unsigned long gui_screen_panic(unsigned long validity, TFT_eSPI* gui) {
        g_system_application.setEnv("gui/screen:animations/name", "panic");
        gui_screen_set("animations:panic", gui_screen_animations);
	return validity;
}

