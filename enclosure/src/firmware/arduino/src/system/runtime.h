#ifndef __ROUNDYPI_SYSTEM_STATUS_H__
#define __ROUNDYPI_SYSTEM_STATUS_H__

#include <string>
#include <map>


class Runtime : public std::map<std::string, std::string> {
	public:
		Runtime();
		bool  isAwake();
		bool  isAsleep();
		void  update();
};

#endif

