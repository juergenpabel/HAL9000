#include <etl/string.h>
#include <ArduinoJson.h>
#include <TimeLib.h>

#include "globals.h"


void on_device_board(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

	if(data.containsKey("identify")) {
		response.clear();
		response["result"] = "OK";
		response["identify"] = JsonObject();
		response["identify"]["board"] = g_device_board.getIdentifier();
		g_util_webserial.send("device/board", response);
	}
	if(data.containsKey("reset")) {
		response.clear();
		response["result"] = "OK";
		response["reset"] = JsonObject();
		g_util_webserial.send("device/board", response, true);
		g_device_board.reset();
	}
}


void on_device_microcontroller(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

	if(data.containsKey("identify")) {
		response.clear();
		response["result"] = "OK";
		response["identify"] = JsonObject();
		response["identify"]["board"] = g_device_microcontroller.getIdentifier();
		g_util_webserial.send("device/microcontroller", response);
	}
	if(data.containsKey("reset")) {
		response.clear();
		response["result"] = "OK";
		response["reset"] = JsonObject();
		g_util_webserial.send("device/microcontroller", response);
		g_device_microcontroller.reset(now());
	}
	if(data.containsKey("halt")) {
		response.clear();
		response["result"] = "OK";
		response["halt"] = JsonObject();
		g_util_webserial.send("device/microcontroller", response);
		g_device_microcontroller.halt();
	}
}


void on_device_display(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

	if(data.containsKey("backlight")) {
		bool  backlight = true;

		response.clear();
		response["backlight"] = JsonObject();
		if(strncmp(data["backlight"].as<const char*>(), "off", 4) == 0) {
			backlight = false;
		}
		if(backlight == true) {
			g_device_board.displayOn();
			response["backlight"]["status"] = "on";
		} else {
			g_device_board.displayOff();
			response["backlight"]["status"] = "off";
		}
		g_util_webserial.send("device/display", response);
	}
}

