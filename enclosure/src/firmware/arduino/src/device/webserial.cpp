#include <ArduinoJson.h>
#include <TimeLib.h>

//TODO:include "device/sdcard/sdcard.h"
#include "device/mcp23X17/mcp23X17.h"
#include "globals.h"


void on_device_board(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	if(data.containsKey("identify")) {
		g_util_webserial.send("device/board#identify", g_device_board.getIdentifier());
	}
}


void on_device_microcontroller(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	if(data.containsKey("identify")) {
		g_util_webserial.send("device/microcontroller#identify", g_device_microcontroller.getIdentifier());
	}
	if(data.containsKey("reset")) {
		g_util_webserial.send("syslog/debug", "device/microcontroller#reset");
		g_device_microcontroller.reset(now(), false);
	}
	if(data.containsKey("halt")) {
		g_util_webserial.send("syslog/debug", "device/microcontroller#halt");
		g_device_microcontroller.halt();
	}
}


void on_device_display(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	if(data.containsKey("backlight")) {
		bool  backlight = true;

		if(strncmp(data["backlight"].as<const char*>(), "off", 4) == 0) {
			backlight = false;
		}
		if(backlight == true) {
			g_device_board.displayOn();
			g_util_webserial.send("device/display#backlight", "\"on\"");
		} else {
			g_device_board.displayOff();
			g_util_webserial.send("device/display#backlight", "\"off\"");
		}
	}
}


void on_device_sdcard(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
/*TODO
	static StaticJsonDocument<1024> json;

	json.clear();
	if(data.containsKey("list")) {
		const char*  directory = "/";
		JsonArray    result;

		result = json.as<JsonArray>();
		if(data["list"].containsKey("directory")) {
			directory = data["list"]["directory"].as<const char*>();
		}
//TODO		g_device_sdcard.list(directory, result);
		for(JsonVariant entry : result) {
			g_util_webserial.send("device/sdcard#list", entry);
		}
	}
	if(data.containsKey("read")) {
		if(data["read"].containsKey("filename")) {
			const char*  filename = "";
			JsonArray    result;

			result = json.as<JsonArray>();
			filename = data["read"]["filename"].as<const char*>();
//TODO			g_device_sdcard.read(filename, result);
			for(JsonVariant entry : result) {
				g_util_webserial.send("device/sdcard#read", entry);
			}
		}
	}
	if(data.containsKey("remove")) {
		if(data["remove"].containsKey("filename")) {
			const char*  filename = "";
			JsonArray    result;

			result = json.as<JsonArray>();
			filename = data["remove"]["filename"].as<const char*>();
//TODO			g_device_sdcard.remove(filename, result);
			g_util_webserial.send("device/sdcard#remove", result);
		}
	}
*/
}


void on_device_mcp23X17(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	if(data.containsKey("init")) {
		uint8_t i2c_bus = 0;
		uint8_t i2c_address = 0;

		if(data["init"].containsKey("i2c-bus")) {
			i2c_bus = data["init"]["i2c-bus"].as<int>();
		}
		if(data["init"].containsKey("i2c-address")) {
			i2c_address = data["init"]["i2c-address"].as<int>();
		}
		g_device_mcp23X17.init(i2c_bus, i2c_address);
	}
	if(data.containsKey("config")) {
		const char*  device_type = nullptr;
		const char*  device_name = nullptr;

		device_type = data["config"]["device"]["type"].as<const char*>();
		device_name = data["config"]["device"]["name"].as<const char*>();
		if(data["config"]["device"].containsKey("inputs")) {
			JsonArray   device_inputs;
			JsonObject  device_events;

			device_inputs = data["config"]["device"]["inputs"].as<JsonArray>();
			device_events = data["config"]["device"]["events"].as<JsonObject>();
			g_device_mcp23X17.config_inputs(device_type, device_name, device_inputs, device_events);
		}
		if(data["config"]["device"].containsKey("outputs")) {
			JsonArray device_outputs;

			device_outputs = data["config"]["device"]["outputs"].as<JsonArray>();
			g_device_mcp23X17.config_outputs(device_type, device_name, device_outputs);
		}
	}
	if(data.containsKey("start")) {
		if(data["start"].as<bool>() == true) {
			g_device_mcp23X17.start();
		}
	}
}

