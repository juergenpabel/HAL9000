#!/usr/bin/env python3

import sys
import os
import os.path
import flet_core
import flet_core.border
import flet_core.colors
import flet
import flet.fastapi as flet_fastapi
from uvicorn import run as uvicorn_run
from fastapi import FastAPI as fastapi_FastAPI
from fastapi.staticfiles import StaticFiles as fastapi_staticfiles_StaticFiles
from logging import getLogger as logging_getLogger, \
                    addLevelName as logging_addLevelName

import hal9000.console.screen.kalliope
import hal9000.console.screen.enclosure
import hal9000.console.screen.system
import hal9000.console.screen.misc


SCREENS = {
	"start": {"src": None, "tooltip": None, "screen": hal9000.console.screen.misc.ScreenStart()},
	"kalliope": {
		"COM": {"src": "/assets/images/COM.jpg", "tooltip": "Kalliope: Synapses",        "screen": hal9000.console.screen.kalliope.ScreenSynapses()},
		"CNT": {"src": "/assets/images/CNT.jpg", "tooltip": "Kalliope: Configuration",   "screen": hal9000.console.screen.kalliope.ScreenConfiguration()},
		"MEM": {"src": "/assets/images/MEM.jpg", "tooltip": "Kalliope: Status",          "screen": hal9000.console.screen.kalliope.ScreenStatus()}
	},
	"enclosure": {
		"VEH": {"src": "/assets/images/VEH.jpg", "tooltip": "Enclosure: Status",         "screen": hal9000.console.screen.enclosure.ScreenStatus()},
		"ATM": {"src": "/assets/images/ATM.jpg", "tooltip": "Enclosure: Sensors",        "screen": hal9000.console.screen.enclosure.ScreenSensors()},
		"GDE": {"src": "/assets/images/GDE.jpg", "tooltip": "Enclosure: Extensions",     "screen": hal9000.console.screen.enclosure.ScreenExtensions()}
	},
	"system": {
		"HIB": {"src": "/assets/images/HIB.jpg", "tooltip": "System: Hibernation",       "screen": hal9000.console.screen.system.ScreenHibernation()},
		"NUC": {"src": "/assets/images/NUC.jpg", "tooltip": "System: Power",             "screen": hal9000.console.screen.system.ScreenPower()},
		"LIF": {"src": "/assets/images/LIF.jpg", "tooltip": "System: Updates",           "screen": hal9000.console.screen.system.ScreenUpdates()},
	},
	"misc": {
		"DMG": {"src": "/assets/images/DMG.jpg", "tooltip": "Miscellaneous: Logs",       "screen": hal9000.console.screen.misc.ScreenLogs()},
		"FLX": {"src": "/assets/images/FLX.jpg", "tooltip": "Miscellaneous: Statistics", "screen": hal9000.console.screen.misc.ScreenStatistics()},
		"NAV": {"src": "/assets/images/NAV.jpg", "tooltip": "Miscellaneous: Help",       "screen": hal9000.console.screen.misc.ScreenHelp()}
	}
}


def console(page: flet.Page):
	page.title = "HAL9000 Console"
	page.theme_mode = flet.ThemeMode.DARK

	menu_lo = flet.Column(width=150)
	menu_li = flet.Column(width=150)
	menu_hal = flet.Column(width=110, controls=[flet.Container(content=flet.Image(src="/assets/images/HAL9000.jpg", fit=flet.ImageFit.FILL),
	                                                           on_click=SCREENS["start"]["screen"].on_show)],
	                       horizontal_alignment=flet.CrossAxisAlignment.CENTER)
	menu_ri = flet.Column(width=150)
	menu_ro = flet.Column(width=150)
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
	page.add(flet.Row(controls=[menu_lo, menu_li, menu_hal, menu_ri, menu_ro], alignment=flet.MainAxisAlignment.CENTER))
	page.add(flet.Row(controls=[flet.Container(border=flet.border.all(1, flet.colors.GREY), border_radius=flet.border_radius.all(10),
	                                           bgcolor=flet.colors.BLACK, content=parent)], alignment=flet.MainAxisAlignment.CENTER))
	page.update()


async def fastapi_lifespan(app: fastapi_FastAPI):
	assets_dir = f'{os.getcwd()}/assets'
	if os.path.islink(assets_dir) is True:
		assets_dir = os.path.realpath(assets_dir)
	app.mount('/assets/', fastapi_staticfiles_StaticFiles(directory=assets_dir, follow_symlink=True), name="assets")
	app.mount('/',       flet_fastapi.app(console, route_url_strategy='path'))
	yield


app = fastapi_FastAPI(lifespan=fastapi_lifespan)
if __name__ == '__main__':
	logging_addLevelName(5, 'TRACE')
	if os.path.exists('assets') is False:
		logging_getLogger().critical("[console] missing 'assets' directory (or symlink to directory)")
		sys_exit(1)
	logging_getLogger().info("[console] starting...")
	try:
		uvicorn_run('console:app', host='0.0.0.0', port=2001, log_level='info')
	except KeyboardInterrupt:
		logging_getLogger().info("[console] exiting due to CTRL-C")
	finally:
		logging_getLogger().info("[console] terminating")

