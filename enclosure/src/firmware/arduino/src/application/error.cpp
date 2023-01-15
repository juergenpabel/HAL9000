#include <etl/string.h>

#include "application/error.h"


Error::Error(const etl::string<GLOBAL_KEY_SIZE>& error_level, const etl::string<GLOBAL_KEY_SIZE>& error_code,const etl::string<GLOBAL_KEY_SIZE>& error_message, uint16_t error_timeout)
      :level(error_level)
      ,code(error_code)
      ,message(error_message)
      ,timeout(error_timeout) {
}

