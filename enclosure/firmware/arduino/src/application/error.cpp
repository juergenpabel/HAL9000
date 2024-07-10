#include <etl/string.h>

#include "globals.h"
#include "application/error.h"


Error::Error(const etl::string<GLOBAL_KEY_SIZE>& error_level, const etl::string<GLOBAL_KEY_SIZE>& error_id,
             const etl::string<GLOBAL_VALUE_SIZE>& error_message, const etl::string<GLOBAL_VALUE_SIZE>& error_detail)
      :level(error_level)
      ,id(error_id)
      ,message(error_message)
      ,detail(error_detail) {
}

etl::string<GLOBAL_VALUE_SIZE>& Error::calculateURL(const etl::string<GLOBAL_KEY_SIZE>& error_id) {
	static etl::string<GLOBAL_VALUE_SIZE> error_url;

	if(error_id.empty() == true) {
		error_url = "https://github.com/juergenpabel/HAL9000/wiki/Error-database";
	} else {
		size_t url_id_offset;

		error_url = g_application.getSetting("application/error:url/template");
		url_id_offset = error_url.find("{id}");
		if(url_id_offset != error_url.npos) {
			error_url = error_url.replace(url_id_offset, 4, error_id);
		}
	}
	return error_url;
}

