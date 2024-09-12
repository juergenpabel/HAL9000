#include <ArduinoJson.h>
#include <TimeLib.h>

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
		response.clear();
		response["reset"] = JsonObject();
		response["result"] = "OK";
		g_util_webserial.send("device/board", response, true);
		g_device_board.reset();
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
		response.clear();
		response["reset"] = JsonObject();
		response["result"] = "OK";
		g_util_webserial.send("device/microcontroller", response);
		g_device_microcontroller.reset(now());
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
			response["result"] = "OK";
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "218";
			response["error"]["level"] = "error";
			response["error"]["title"] = "Peripheral error";
			response["error"]["details"] = "request for topic 'device/mcp23X17' with operation 'init': MCP23X17::init() failed";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["i2c-bus"] = i2c_bus;
			response["error"]["data"]["i2c-address"] = i2c_address;
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
				response["result"] = "OK";
			} else {
				response["result"] = "error";
				response["error"] = JsonObject();
				response["error"]["id"] = "218";
				response["error"]["level"] = "error";
				response["error"]["title"] = "Peripheral error";
				response["error"]["details"] = "request for topic 'device/mcp23X17' with operation 'config': MCP23X17::config_inputs() failed";
				response["error"]["data"] = JsonObject();
				response["error"]["data"]["type"] = device_type;
				response["error"]["data"]["name"] = device_name;
				response["error"]["data"]["inputs"] = device_inputs;
				response["error"]["data"]["events"] = device_events;
			}
		}
		if(data["config"]["device"].containsKey("outputs")) {
			JsonArray device_outputs;

			device_outputs = data["config"]["device"]["outputs"].as<JsonArray>();
			if(g_device_mcp23X17.config_outputs(device_type, device_name, device_outputs) == true) {
				response["result"] = "OK";
			} else {
				response["result"] = "error";
				response["error"] = JsonObject();
				response["error"]["id"] = "218";
				response["error"]["level"] = "error";
				response["error"]["title"] = "Peripheral error";
				response["error"]["details"] = "request for topic 'device/mcp23X17' with operation 'config': MCP23X17::config_outputs() failed";
				response["error"]["data"] = JsonObject();
				response["error"]["data"]["type"] = device_type;
				response["error"]["data"]["name"] = device_name;
				response["error"]["data"]["outputs"] = device_outputs;
			}
		}
		g_util_webserial.send("device/mcp23X17", response);
	}
	if(data.containsKey("start")) {
		bool run_as_task = false;

		response.clear();
		response["start"] = JsonObject();
		if(data["start"].containsKey("task")) {
			run_as_task = data["start"]["task"].as<bool>();
		}
		if(g_device_mcp23X17.start(run_as_task) == true) {
			response["result"] = "OK";
		} else {
			response["result"] = "error";
			response["error"] = JsonObject();
			response["error"]["id"] = "218";
			response["error"]["level"] = "error";
			response["error"]["title"] = "Peripheral error";
			response["error"]["details"] = "request for topic 'device/mcp23X17' with operation 'start': MCP23X17::start() failed";
			response["error"]["data"] = JsonObject();
			response["error"]["data"]["task"] = run_as_task;
		}
		g_util_webserial.send("device/mcp23X17", response);
	}
}

