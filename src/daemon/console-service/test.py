#!/usr/bin/python3

import flet as ft

from flet_routed_app import RoutedApp
from hal9000.daemon.console import MainViewBuilder

def main(page: ft.Page):
	app = RoutedApp(page)
	app.add_view_builders([MainViewBuilder])

ft.app(target=main)

