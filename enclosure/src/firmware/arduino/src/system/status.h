#ifndef __ROUNDYPI_SYSTEM_STATUS_H__
#define __ROUNDYPI_SYSTEM_STATUS_H__

#include <string>
#include <map>


class Status : public std::map<std::string, std::string> {
	public:
		Status();
		bool  isAwake();
		bool  isAsleep();
		void  update();
};

#endif

