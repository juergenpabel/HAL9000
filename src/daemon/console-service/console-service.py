#!/usr/bin/python3

import flet
import flet.border
import flet.colors

import hal9000.console.screen.kalliope
import hal9000.console.screen.enclosure
import hal9000.console.screen.system
import hal9000.console.screen.misc


def hal9000_screens():
	screens = {}
	screens["kalliope"] = dict()
	screens["kalliope"]["COM"]  = {"src": "COM.jpeg", "tooltip": "Kalliope: Orders",          "screen": hal9000.console.screen.kalliope.ScreenOrder()}
	screens["kalliope"]["CNT"]  = {"src": "CNT.jpeg", "tooltip": "Kalliope: Configuration",   "screen": hal9000.console.screen.kalliope.ScreenConfiguration()}
	screens["kalliope"]["MEM"]  = {"src": "MEM.jpeg", "tooltip": "Kalliope: Status",          "screen": hal9000.console.screen.kalliope.ScreenStatus()}
	screens["enclosure"] = dict()
	screens["enclosure"]["VEH"] = {"src": "VEH.jpeg", "tooltip": "Enclosure: Status",         "screen": hal9000.console.screen.enclosure.ScreenStatus()}
	screens["enclosure"]["ATM"] = {"src": "ATM.jpeg", "tooltip": "Enclosure: Sensors",        "screen": hal9000.console.screen.enclosure.ScreenSensors()}
	screens["enclosure"]["GDE"] = {"src": "GDE.jpeg", "tooltip": "Enclosure: Extensions",     "screen": hal9000.console.screen.enclosure.ScreenExtensions()}
	screens["system"] = dict()
	screens["system"]["HIB"]    = {"src": "HIB.jpeg", "tooltip": "System: Hibernation",       "screen": hal9000.console.screen.system.ScreenHibernation()}
	screens["system"]["NUC"]    = {"src": "NUC.jpeg", "tooltip": "System: Power",             "screen": hal9000.console.screen.system.ScreenPower()}
	screens["system"]["LIF"]    = {"src": "LIF.jpeg", "tooltip": "System: Updates",           "screen": hal9000.console.screen.system.ScreenUpdates()}
	screens["misc"] = dict()
	screens["misc"]["DMG"]      = {"src": "DMG.jpeg", "tooltip": "Miscellaneous: Logs",       "screen": hal9000.console.screen.misc.ScreenLogs()}
	screens["misc"]["FLX"]      = {"src": "FLX.jpeg", "tooltip": "Miscellaneous: Statistics", "screen": hal9000.console.screen.misc.ScreenStatistics()}
	screens["misc"]["NAV"]      = {"src": "NAV.jpeg", "tooltip": "Miscellaneous: Help",       "screen": hal9000.console.screen.misc.ScreenHelp()}
	return screens


def main(page: flet.Page):
	page.title = "HAL9000 Console"
	page.theme_mode = flet.ThemeMode.DARK

	menu_lo = flet.Column(width=150)
	menu_li = flet.Column(width=150)
	hal9000 = flet.Column(width=110, controls=[flet.Image(src="HAL9000.jpg", fit=flet.ImageFit.FILL)],
	                      horizontal_alignment=flet.CrossAxisAlignment.CENTER)
	menu_ri = flet.Column(width=150)
	menu_ro = flet.Column(width=150)
	screen = flet.AnimatedSwitcher(content=flet.Container(width=750, height=500),
	                               transition=flet.AnimatedSwitcherTransition.FADE,
	                               switch_in_curve=flet.AnimationCurve.EASE_OUT,
	                               switch_out_curve=flet.AnimationCurve.EASE_IN)
	screens = hal9000_screens()
	for subsystem, column in {"kalliope": menu_lo, "enclosure": menu_li, "system": menu_ri, "misc": menu_ro}.items():
		if subsystem in screens:
			for module in screens[subsystem].keys():
				screens[subsystem][module]["screen"].setContext(page, screen)
				column.controls.append(flet.Container(content=flet.Image(src=screens[subsystem][module]["src"],
				                                                         tooltip=screens[subsystem][module]["tooltip"],
				                                                         fit=flet.ImageFit.FILL,
				                                                         border_radius=flet.border_radius.all(5)),
				                                      on_click=screens[subsystem][module]["screen"].on_show))
	page.add(flet.Row(controls=[menu_lo, menu_li, hal9000, menu_ri, menu_ro], alignment=flet.MainAxisAlignment.CENTER))
	page.add(flet.Row(controls=[flet.Container()], height=25))
	page.add(flet.Row(controls=[screen], alignment=flet.MainAxisAlignment.CENTER))
	page.update()


import logging
logging.getLogger().setLevel(logging.DEBUG)
flet.app(target=main, name="", host='127.0.0.1', port=9000, route_url_strategy="path", view=None, assets_dir="assets")

