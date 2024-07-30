#ifndef __GUI_GUI_H__
#define __GUI_GUI_H__

typedef enum {
	RefreshIgnore = 0x00,
	RefreshScreen = 0x01,
	RefreshOverlay = 0x02,
	RefreshAll = 0x03
} gui_refresh_t;

void gui_update();

#endif

