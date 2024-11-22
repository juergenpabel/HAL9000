#!/usr/bin/env python3

from sys import exit as sys_exit
from os import getcwd as os_getcwd
from os.path import exists as os_path_exists, \
                    islink as os_path_islink, \
                    realpath as os_path_realpath

from flet import Page as flet_Page, \
                 Row as flet_Row ,\
                 Column as flet_Column ,\
                 ThemeMode as flet_ThemeMode, \
import flet
from flet.fastapi import app as flet_fastapi_app
from uvicorn import run as uvicorn_run
from uvicorn.config import LOGGING_CONFIG as uvicorn_config_LOGGING_CONFIG
from fastapi import FastAPI as fastapi_FastAPI
from fastapi.staticfiles import StaticFiles as fastapi_staticfiles_StaticFiles
from logging import getLogger as logging_getLogger, \
                    addLevelName as logging_addLevelName

import hal9000.dashboard.screen.kalliope
import hal9000.dashboard.screen.enclosure
import hal9000.dashboard.screen.system
import hal9000.dashboard.screen.misc


SCREENS = {
	"start": {"src": None, "tooltip": None, "screen": hal9000.dashboard.screen.misc.ScreenStart()},
	"kalliope": {
		"COM": {"src": "/resources/images/COM.jpg", "tooltip": "Kalliope: Synapses",        "screen": hal9000.dashboard.screen.kalliope.ScreenSynapses()},
		"CNT": {"src": "/resources/images/CNT.jpg", "tooltip": "Kalliope: Configuration",   "screen": hal9000.dashboard.screen.kalliope.ScreenConfiguration()},
		"MEM": {"src": "/resources/images/MEM.jpg", "tooltip": "Kalliope: Status",          "screen": hal9000.dashboard.screen.kalliope.ScreenStatus()}
	},
	"enclosure": {
		"VEH": {"src": "/resources/images/VEH.jpg", "tooltip": "Enclosure: Status",         "screen": hal9000.dashboard.screen.enclosure.ScreenStatus()},
		"ATM": {"src": "/resources/images/ATM.jpg", "tooltip": "Enclosure: Sensors",        "screen": hal9000.dashboard.screen.enclosure.ScreenSensors()},
		"GDE": {"src": "/resources/images/GDE.jpg", "tooltip": "Enclosure: Extensions",     "screen": hal9000.dashboard.screen.enclosure.ScreenExtensions()}
	},
	"system": {
		"HIB": {"src": "/resources/images/HIB.jpg", "tooltip": "System: Hibernation",       "screen": hal9000.dashboard.screen.system.ScreenHibernation()},
		"NUC": {"src": "/resources/images/NUC.jpg", "tooltip": "System: Power",             "screen": hal9000.dashboard.screen.system.ScreenPower()},
		"LIF": {"src": "/resources/images/LIF.jpg", "tooltip": "System: Updates",           "screen": hal9000.dashboard.screen.system.ScreenUpdates()},
	},
	"misc": {
		"DMG": {"src": "/resources/images/DMG.jpg", "tooltip": "Miscellaneous: Logs",       "screen": hal9000.dashboard.screen.misc.ScreenLogs()},
		"FLX": {"src": "/resources/images/FLX.jpg", "tooltip": "Miscellaneous: Statistics", "screen": hal9000.dashboard.screen.misc.ScreenStatistics()},
		"NAV": {"src": "/resources/images/NAV.jpg", "tooltip": "Miscellaneous: Help",       "screen": hal9000.dashboard.screen.misc.ScreenHelp()}
	}
}


def dashboard(page: flet_Page):
	page.title = "HAL9000 Dashboard"
	page.theme_mode = flet_ThemeMode.DARK

	menu_lo = flet_Column(width=150)
	menu_li = flet_Column(width=150)
	menu_hal = flet_Column(width=110, controls=[flet.Container(content=flet.Image(src="/resources/images/HAL9000.jpg", fit=flet.ImageFit.FILL),
	                                                           on_click=SCREENS["start"]["screen"].on_show)],
	                       horizontal_alignment=flet.CrossAxisAlignment.CENTER)
	menu_ri = flet_Column(width=150)
	menu_ro = flet_Column(width=150)
	parent = flet.AnimatedSwitcher(width=750, height=400, content=SCREENS["start"]["screen"],
	                               transition=flet.AnimatedSwitcherTransition.FADE,
	                               switch_in_curve=flet.AnimationCurve.EASE_OUT,
	                               switch_out_curve=flet.AnimationCurve.EASE_IN)
	SCREENS["start"]["screen"].setContext(page, parent)
	for subsystem, column in {"kalliope": menu_lo, "enclosure": menu_li, "system": menu_ri, "misc": menu_ro}.items():
		for module in SCREENS[subsystem].keys():
			SCREENS[subsystem][module]["screen"].setContext(page, parent)
			column.controls.append(flet.Container(expand=False,
                                                              content=flet.Image(src=SCREENS[subsystem][module]["src"],
				                                                 tooltip=SCREENS[subsystem][module]["tooltip"],
				                                                 fit=flet.ImageFit.FILL,
				                                                 border_radius=flet.border_radius.all(5)),
				                              on_click=SCREENS[subsystem][module]["screen"].on_show))
	page.add(flet_Row(controls=[menu_lo, menu_li, menu_hal, menu_ri, menu_ro], alignment=flet.MainAxisAlignment.CENTER))
	page.add(flet_Row(controls=[flet.Container(border=flet.border.all(1, flet.colors.GREY), border_radius=flet.border_radius.all(10),
	                                           bgcolor=flet.colors.BLACK, content=parent)], alignment=flet.MainAxisAlignment.CENTER))
	page.update()


async def fastapi_lifespan(app: fastapi_FastAPI):
	resources_dir = f'{os_getcwd()}/resources'
	if os_path_islink(resources_dir) is True:
		resources_dir = os_path_realpath(resources_dir)
	app.mount('/resources/', fastapi_staticfiles_StaticFiles(directory=resources_dir, follow_symlink=True), name="resources")
	app.mount('/',           flet_fastapi_app(dashboard, route_url_strategy='path'))
	yield


app = fastapi_FastAPI(lifespan=fastapi_lifespan)
if __name__ == '__main__':
	logging_addLevelName(5, 'TRACE')
	if os_path_exists('resources') is False:
		logging_getLogger().critical("[dashboard] missing 'resources' directory (or symlink to directory)")
		sys_exit(1)
	logging_getLogger().info("[dashboard] starting...")
	try:
		uvicorn_config_LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s %(levelprefix)s %(message)s"
		uvicorn_run('dashboard:app', host='0.0.0.0', port=2001, log_level='info')
	except KeyboardInterrupt:
		logging_getLogger().info("[dashboard] exiting due to CTRL-C")
	finally:
		logging_getLogger().info("[dashboard] terminating")

