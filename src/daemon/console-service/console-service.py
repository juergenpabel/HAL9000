#!/usr/bin/python3

import flet as ft
import logging

def main(page: ft.Page):
    page.title = "HAL9000 Console"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 50
    page.update()

    hal9000 = ft.Image(src="HAL9000.jpg", width=160)
    menu_lo = ft.Column(width=160)
    menu_li = ft.Column(width=160)
    menu_ri = ft.Column(width=160)
    menu_ro = ft.Column(width=160)
    row_menu = ft.Row(controls=[menu_lo, menu_li, hal9000, menu_ri, menu_ro])
    screen = ft.AnimatedSwitcher(ft.Container(), transition=ft.AnimatedSwitcherTransition.FADE,switch_in_curve=ft.AnimationCurve.EASE_OUT,switch_out_curve=ft.AnimationCurve.EASE_IN, width=800, height=600)
    row_screen = ft.Row(controls=[screen])
    page.add(row_menu)
    page.add(row_screen)

    def menu_clicked(e):
        screen.content = ft.Container(content=ft.Image(src=e.control.content.src, width=800, height=600, border_radius=ft.border_radius.all(10)))
        screen.update()
        page.go("/"+e.control.content.src[0:-5])


    for filename, tooltip in {'COM.jpeg': 'Kalliope: Orders', 'CNT.jpeg': 'Kalliope: Configuration', 'MEM.jpeg': 'Kalliope: Status'}.items():
        menu_lo.controls.append(ft.Container(
                               content=ft.Image(src=f"{filename}", tooltip=tooltip, width=160, height=90, border_radius=ft.border_radius.all(5)),
                               on_click=menu_clicked))
    for filename, tooltip in {'VEH.jpeg': 'Enclosure: Status', 'ATM.jpeg': 'Enclosure: Sensors', 'GDE.jpeg': 'Enclosure: Extension'}.items():
        menu_li.controls.append(ft.Container(
                               content=ft.Image(src=f"{filename}", tooltip=tooltip, width=160, height=90, border_radius=ft.border_radius.all(5)),
                               on_click=menu_clicked))
    for filename, tooltip in {'HIB.jpeg': 'System: Hibernation', 'NUC.jpeg': 'System: Power', 'LIF.jpeg': 'System: Updates'}.items():
        menu_ri.controls.append(ft.Container(
                               content=ft.Image(src=f"{filename}", tooltip=tooltip, width=160, height=90, border_radius=ft.border_radius.all(5)),
                               on_click=menu_clicked))
    for filename, tooltip in {'DMG.jpeg': 'Misc: logs', 'FLX.jpeg': 'Misc: statistics', 'NAV.jpeg': 'Misc: Help'}.items():
        menu_ro.controls.append(ft.Container(
                               content=ft.Image(src=f"{filename}", tooltip=tooltip, width=160, height=90, border_radius=ft.border_radius.all(5)),
                               on_click=menu_clicked))
    page.update()

logging.getLogger().setLevel(logging.DEBUG)
ft.app(target=main, name="", host='127.0.0.1', port=9000, route_url_strategy="path", view=None, assets_dir="assets")

