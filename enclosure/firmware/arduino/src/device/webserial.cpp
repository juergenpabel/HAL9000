#include <ArduinoJson.h>
#include <TimeLib.h>

//TODO:include "device/sdcard/sdcard.h"
#include "device/mcp23X17/mcp23X17.h"
#include "globals.h"


void on_device_board(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

	if(data.containsKey("identify")) {
		response.clear();
		response["identify"] = JsonObject();
		response["identify"]["board"] = g_device_board.getIdentifier().c_str();
		g_util_webserial.send("device/board", response);
	}
	if(data.containsKey("reset")) {
		bool  host_rebooting = false;

		if(data["reset"].containsKey("reboot")) {
			if(strncmp(data["reset"]["reboot"].as<const char*>(), "true", 5) == 0) {
				host_rebooting = true;
			}
		}
		response.clear();
		response["reset"] = JsonObject();
		response["reset"]["reboot"] = host_rebooting;
		g_util_webserial.send("device/board", response);
		g_device_board.reset(host_rebooting);
	}
}


void on_device_microcontroller(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

	if(data.containsKey("identify")) {
		response.clear();
		response["identify"] = JsonObject();
		response["identify"]["board"] = g_device_microcontroller.getIdentifier().c_str();
		g_util_webserial.send("device/microcontroller", response);
	}
	if(data.containsKey("reset")) {
		bool  host_rebooting = false;

		if(data["reset"].containsKey("reboot")) {
			if(strncmp(data["reset"]["reboot"].as<const char*>(), "true", 5) == 0) {
				host_rebooting = true;
			}
		}
		response.clear();
		response["reset"] = JsonObject();
		response["reset"]["reboot"] = host_rebooting;
		g_util_webserial.send("device/microcontroller", response);
		g_device_microcontroller.reset(now(), host_rebooting);
	}
	if(data.containsKey("halt")) {
		response.clear();
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


void on_device_sdcard(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
/*TODO
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

	if(data.containsKey("list")) {
		const char*  directory = "/";
		JsonArray    result;

		response.clear();
		result = response.as<JsonArray>();
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

			response.clear();
			result = response.as<JsonArray>();
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

			response.clear();
			result = response.as<JsonArray>();
			filename = data["remove"]["filename"].as<const char*>();
//TODO			g_device_sdcard.remove(filename, result);
			g_util_webserial.send("device/sdcard#remove", result);
		}
	}
*/
}


void on_device_mcp23X17(const etl::string<GLOBAL_KEY_SIZE>& command, const JsonVariant& data) {
	static StaticJsonDocument<GLOBAL_VALUE_SIZE*2> response;

	if(data.containsKey("init")) {
		uint8_t i2c_bus = 0;
		uint8_t i2c_address = 0;

		response.clear();
		response["init"] = JsonObject();
		if(data["init"].containsKey("i2c-bus")) {
			i2c_bus = data["init"]["i2c-bus"].as<int>();
		}
		if(data["init"].containsKey("i2c-address")) {
			i2c_address = data["init"]["i2c-address"].as<int>();
		}
		if(g_device_mcp23X17.init(i2c_bus, i2c_address) == true) {
			response["init"]["i2c-bus"] = i2c_bus;
			response["init"]["i2c-address"] = i2c_address;
		} else {
			response["init"]["error"] = "init failed"; //TODO:error codes
		}
		g_util_webserial.send("device/mcp23X17", response);
	}
	if(data.containsKey("config")) {
		const char*  device_type = nullptr;
		const char*  device_name = nullptr;

		response.clear();
		response["config"] = JsonObject();
		device_type = data["config"]["device"]["type"].as<const char*>();
		device_name = data["config"]["device"]["name"].as<const char*>();
		if(data["config"]["device"].containsKey("inputs")) {
			JsonArray   device_inputs;
			JsonObject  device_events;

			device_inputs = data["config"]["device"]["inputs"].as<JsonArray>();
			device_events = data["config"]["device"]["events"].as<JsonObject>();
			if(g_device_mcp23X17.config_inputs(device_type, device_name, device_inputs, device_events) == true) {
				response["config"]["inputs"] = "OK";
			} else {
				response["config"]["inputs"] = "error"; //TODO:error codes
			}
		}
		if(data["config"]["device"].containsKey("outputs")) {
			JsonArray device_outputs;

			device_outputs = data["config"]["device"]["outputs"].as<JsonArray>();
			if(g_device_mcp23X17.config_outputs(device_type, device_name, device_outputs) == true) {
				response["config"]["outputs"] = "OK";
			} else {
				response["config"]["outputs"] = "error"; //TODO:error codes
			}
		}
		g_util_webserial.send("device/mcp23X17", response);
	}
	if(data.containsKey("start")) {
		response.clear();
		response["start"] = JsonObject();
		if(g_device_mcp23X17.start() == true) {
			response["start"]["result"] = "OK";
		} else {
			response["start"]["error"] = "start failed"; //TODO:error codes
		}
		g_util_webserial.send("device/mcp23X17", response);
	}
}

