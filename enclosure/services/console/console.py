#!/usr/bin/env python3

import os
import sys
import flet_core
import flet_core.border
import flet_core.colors
import flet

import hal9000.console.screen.kalliope
import hal9000.console.screen.enclosure
import hal9000.console.screen.system
import hal9000.console.screen.misc


SCREENS = {
	"start": {"src": None, "tooltip": None, "screen": hal9000.console.screen.misc.ScreenStart()},
	"kalliope": {
		"COM": {"src": "COM.jpg", "tooltip": "Kalliope: Synapses",        "screen": hal9000.console.screen.kalliope.ScreenSynapses()},
		"CNT": {"src": "CNT.jpg", "tooltip": "Kalliope: Configuration",   "screen": hal9000.console.screen.kalliope.ScreenConfiguration()},
		"MEM": {"src": "MEM.jpg", "tooltip": "Kalliope: Status",          "screen": hal9000.console.screen.kalliope.ScreenStatus()}
	},
	"enclosure": {
		"VEH": {"src": "VEH.jpg", "tooltip": "Enclosure: Status",         "screen": hal9000.console.screen.enclosure.ScreenStatus()},
		"ATM": {"src": "ATM.jpg", "tooltip": "Enclosure: Sensors",        "screen": hal9000.console.screen.enclosure.ScreenSensors()},
		"GDE": {"src": "GDE.jpg", "tooltip": "Enclosure: Extensions",     "screen": hal9000.console.screen.enclosure.ScreenExtensions()}
	},
	"system": {
		"HIB": {"src": "HIB.jpg", "tooltip": "System: Hibernation",       "screen": hal9000.console.screen.system.ScreenHibernation()},
		"NUC": {"src": "NUC.jpg", "tooltip": "System: Power",             "screen": hal9000.console.screen.system.ScreenPower()},
		"LIF": {"src": "LIF.jpg", "tooltip": "System: Updates",           "screen": hal9000.console.screen.system.ScreenUpdates()},
	},
	"misc": {
		"DMG": {"src": "DMG.jpg", "tooltip": "Miscellaneous: Logs",       "screen": hal9000.console.screen.misc.ScreenLogs()},
		"FLX": {"src": "FLX.jpg", "tooltip": "Miscellaneous: Statistics", "screen": hal9000.console.screen.misc.ScreenStatistics()},
		"NAV": {"src": "NAV.jpg", "tooltip": "Miscellaneous: Help",       "screen": hal9000.console.screen.misc.ScreenHelp()}
	}
}


def main(page: flet.Page):
	page.title = "HAL9000 Console"
	page.theme_mode = flet.ThemeMode.DARK

	menu_lo = flet.Column(width=150)
	menu_li = flet.Column(width=150)
	menu_hal = flet.Column(width=110, controls=[flet.Container(content=flet.Image(src="HAL9000.jpg", fit=flet.ImageFit.FILL),
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


os.environ["FLET_FORCE_WEB_SERVER"] = "1"
import logging
logging.getLogger().setLevel(logging.INFO)
app = flet.app(main, host='0.0.0.0', port=8080, route_url_strategy="path", view=None, assets_dir=f"{os.getcwd()}/assets")

