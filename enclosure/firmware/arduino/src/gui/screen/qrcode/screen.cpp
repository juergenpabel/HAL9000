#include <etl/string.h>
#include <etl/format_spec.h>
#include <etl/to_string.h>
#include <qrcodegen.h>

#include "gui/screen/screen.h"
#include "gui/screen/idle/screen.h"
#include "globals.h"

#define QRCODE_VERSION APPLICATION_ERROR_QRCODE_VERSION
#define QRCODE_SIZE    qrcodegen_BUFFER_LEN_FOR_VERSION(QRCODE_VERSION)
#define QRCODE_ECC_HELPER1(name,level) name##_##level
#define QRCODE_ECC_HELPER2(name,level) QRCODE_ECC_HELPER1(name,level)
#define QRCODE_ECC QRCODE_ECC_HELPER2(qrcodegen_Ecc, APPLICATION_ERROR_QRCODE_ECC)

typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, uint32_t, 8> ColorMap;
static ColorMap g_colors = {{"black",  TFT_BLACK},
                            {"white",  TFT_WHITE},
                            {"red",    TFT_RED},
                            {"green",  TFT_GREEN},
                            {"blue",   TFT_BLUE},
                            {"yellow", TFT_YELLOW},
                            {"orange", TFT_ORANGE},
                            {"silver", TFT_SILVER}};

typedef etl::map<etl::string<GLOBAL_KEY_SIZE>, uint32_t, 3> TextsizeMap;
static TextsizeMap g_textsizes = {{"small",  1},
                                  {"normal", 2},
                                  {"large",  3}};


void gui_screen_qrcode(bool refresh) {
	etl::string<GLOBAL_VALUE_SIZE> text_above;
	etl::string<GLOBAL_VALUE_SIZE> text_url;
	etl::string<GLOBAL_VALUE_SIZE> text_below;

	if(refresh == true) {
		uint32_t color_screen = TFT_BLACK;
		uint32_t color_text = TFT_WHITE;
		uint32_t textsize_above = 2;
		uint32_t textsize_below = 2;

		if(g_application.hasEnv("gui/screen:qrcode/text-above") == true) {
			text_above = g_application.getEnv("gui/screen:qrcode/text-above");
		}
		if(g_application.hasEnv("gui/screen:qrcode/text-url") == true) {
			text_url = g_application.getEnv("gui/screen:qrcode/text-url");
		}
		if(g_application.hasEnv("gui/screen:qrcode/text-below") == true) {
			text_below = g_application.getEnv("gui/screen:qrcode/text-below");
		}
		if(g_application.hasEnv("gui/screen:qrcode/color-screen") == true) {
			ColorMap::iterator iter = g_colors.find(g_application.getEnv("gui/screen:qrcode/color-screen"));
			if(iter != g_colors.end()) {
				color_screen = iter->second;
			}
		}
		if(g_application.hasEnv("gui/screen:qrcode/color-text") == true) {
			ColorMap::iterator iter = g_colors.find(g_application.getEnv("gui/screen:qrcode/color-text"));
			if(iter != g_colors.end()) {
				color_text = iter->second;
			}
		}
		if(g_application.hasEnv("gui/screen:qrcode/textsize-above") == true) {
			TextsizeMap::iterator iter = g_textsizes.find(g_application.getEnv("gui/screen:qrcode/textsize-above"));
			if(iter != g_textsizes.end()) {
				textsize_above = iter->second;
			}
		}
		if(g_application.hasEnv("gui/screen:qrcode/textsize-below") == true) {
			TextsizeMap::iterator iter = g_textsizes.find(g_application.getEnv("gui/screen:qrcode/textsize-below"));
			if(iter != g_textsizes.end()) {
				textsize_below = iter->second;
			}
		}
		g_gui.fillScreen(color_screen);
		if(text_above.size() > 0) {
			uint16_t pos_x;
			uint16_t pos_y;

			pos_x = (TFT_WIDTH -GUI_SCREEN_WIDTH )/2+(GUI_SCREEN_WIDTH /2);
			pos_y = (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*2);
			g_gui.setTextColor(color_text, color_screen, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(textsize_above);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.setTextWrap(true);
			g_gui.drawString(text_above.c_str(), pos_x, pos_y-g_gui.fontHeight()-5);
		}
		if(text_url.size() > 0) {
			static uint8_t qr_temp[QRCODE_SIZE];
			static uint8_t qr_final[QRCODE_SIZE];

			if(qrcodegen_encodeText(text_url.c_str(), qr_temp, qr_final, QRCODE_ECC, QRCODE_VERSION, QRCODE_VERSION, qrcodegen_Mask_AUTO, true) == true) {
				int      qr_size;
				uint16_t qr_dotsize;
				uint16_t offset_x;
				uint16_t offset_y;

				qr_size = qrcodegen_getSize(qr_final);
				qr_dotsize = (min(GUI_SCREEN_WIDTH, GUI_SCREEN_HEIGHT) / 8 * 4) / qr_size;

				offset_x = ((TFT_WIDTH -GUI_SCREEN_WIDTH )/2)+(((GUI_SCREEN_WIDTH )-(qr_dotsize*qr_size))/2);
				offset_y = ((TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2)+(((GUI_SCREEN_HEIGHT)-(qr_dotsize*qr_size))/2);
				g_gui.fillRoundRect(offset_x-(qr_dotsize*1), offset_y-(qr_dotsize*1), (1+qr_size+1)*qr_dotsize, (1+qr_size+1)*qr_dotsize, qr_dotsize*1, TFT_WHITE);
				for(uint8_t y=0; y<qr_size; y++) {
					for(uint8_t x=0; x<qr_size; x++) {
						if(qrcodegen_getModule(qr_final, x, y) == true) {
							g_gui.fillRect(offset_x+(qr_dotsize*x), offset_y+(qr_dotsize*y), qr_dotsize, qr_dotsize, TFT_BLACK);
						}
					}
				}
			}
		}
		if(text_below.size() > 0) {
			uint16_t pos_x;
			uint16_t pos_y;

			pos_x = (TFT_WIDTH -GUI_SCREEN_WIDTH )/2+(GUI_SCREEN_WIDTH /2);
			pos_y = (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*6);
			g_gui.setTextColor(color_text, color_screen, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(textsize_below);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.drawString(text_below.c_str(), pos_x, pos_y+g_gui.fontHeight()+5);
		}
	}
}

