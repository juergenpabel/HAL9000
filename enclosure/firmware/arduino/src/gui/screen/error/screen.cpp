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


void gui_screen_error(bool refresh) {
	if(refresh == true) {
		static etl::string<GLOBAL_VALUE_SIZE> error_message;
		static etl::string<GLOBAL_VALUE_SIZE> error_code;
		static etl::string<GLOBAL_VALUE_SIZE> error_url;

		error_message.empty();
		error_code.empty();
		error_url.empty();
		if(g_application.hasEnv("gui/screen:error/message") == true) {
			error_message = g_application.getEnv("gui/screen:error/message");
		}
		if(g_application.hasEnv("gui/screen:error/code") == true) {
			error_code = g_application.getEnv("gui/screen:error/code");
			if(g_application.hasSetting("application/help:error/base-url") == true) {
				error_url  = g_application.getSetting("application/help:error/base-url");
				error_url += error_code;
			}
		}
		g_gui.fillScreen(TFT_RED);
		if(error_message.size() > 0) {
			uint16_t pos_x;
			uint16_t pos_y;

			pos_x = (TFT_WIDTH -GUI_SCREEN_WIDTH )/2+(GUI_SCREEN_WIDTH /2);
			pos_y = (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*2);
			g_gui.setTextColor(TFT_WHITE, TFT_RED, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(1);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.setTextWrap(true);
			g_gui.drawString(error_message.c_str(), pos_x, pos_y-g_gui.fontHeight()-5);
		}
		if(error_code.size() > 0) {
			uint16_t pos_x;
			uint16_t pos_y;

			pos_x = (TFT_WIDTH -GUI_SCREEN_WIDTH )/2+(GUI_SCREEN_WIDTH /2);
			pos_y = (TFT_HEIGHT-GUI_SCREEN_HEIGHT)/2+(GUI_SCREEN_HEIGHT/8*6);
			g_gui.setTextColor(TFT_WHITE, TFT_RED, false);
			g_gui.setTextFont(1);
			g_gui.setTextSize(2);
			g_gui.setTextDatum(MC_DATUM);
			g_gui.drawString(error_code.insert(0, "Error ").c_str(), pos_x, pos_y+g_gui.fontHeight()+5);
		}
		if(error_url.size() > 0) {
			static uint8_t qr_temp[QRCODE_SIZE];
			static uint8_t qr_final[QRCODE_SIZE];

			if(qrcodegen_encodeText(error_url.c_str(), qr_temp, qr_final, QRCODE_ECC, QRCODE_VERSION, QRCODE_VERSION, qrcodegen_Mask_AUTO, true) == true) {
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
	}
}

