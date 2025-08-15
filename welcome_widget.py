#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
import os
import gettext
import locale

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# Import GLib for the timer and Adw for the animation
from gi.repository import Gtk, Adw, Gdk, GLib

# --- i18n Setup ---
WIDGET_NAME = "linexin-installer-welcome-widget"
LOCALE_DIR = "/usr/share/locale"
locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain(WIDGET_NAME, LOCALE_DIR)
gettext.bindtextdomain(WIDGET_NAME, LOCALE_DIR)
gettext.textdomain(WIDGET_NAME)
_ = gettext.gettext


class WelcomeWidget(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # --- Language Lists for Animation ---
        self.translations = [
            "Welcome to", "Witaj w", "Bienvenido a", "Bienvenue à",
            "Willkommen bei", "Benvenuto in", "Bem-vindo a", "Добро пожаловать в",
            "へようこそ", "欢迎来到", "مرحبا بك في", "में आपका स्वागत है", "Welkom bij",
            "Välkommen till", "'a hoş geldiniz", "에 오신 것을 환영합니다", "Καλώς ήρθατε στο",
            "Ласкаво просимо до", "Vítejte v", "Tervetuloa"
        ]
        # **NEW:** A parallel list of translations for the button.
        self.button_translations = [
            "Begin Installation", "Rozpocznij instalację", "Iniciar instalación", "Commencer l'installation",
            "Installation beginnen", "Inizia l'installazione", "Iniciar instalação", "Начать установку",
            "インストールを開始", "开始安装", "بدء التثبيت", "इंस्टॉलेशन शुरू करें", "Installatie beginnen",
            "Påbörja installationen", "Kuruluma Başla", "설치 시작", "Έναρξη εγκατάστασης",
            "Почати встановлення", "Zahájit instalaci", "Aloita asennus"
        ]
        self.current_lang_index = 0

        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "images", "logo.png")

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(15)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)

        self.welcome_label = Gtk.Label()
        self.welcome_label.set_margin_top(80)
        self.welcome_label.add_css_class("welcome_text")
        self.welcome_label.set_markup(f'<span weight="bold">{_("Welcome to")}</span>')
        self.append(self.welcome_label)

        welcome_image = Gtk.Picture.new_for_filename(image_path)
        welcome_image.set_margin_start(70)
        welcome_image.set_margin_end(70)
        welcome_image.set_can_shrink(True)
        self.append(welcome_image)

        button_box = Gtk.Box(halign=Gtk.Align.CENTER, spacing=12)
        # Set the initial button text using the locale
        self.btn_install = Gtk.Button(label=_("Begin Installation"))
        self.btn_install.add_css_class("suggested-action")
        self.btn_install.add_css_class("proceed_button")
        self.btn_install.set_margin_top(80)
        self.btn_install.set_margin_bottom(80)
        button_box.append(self.btn_install)
        self.append(button_box)

        # --- Animation Setup ---
        GLib.timeout_add_seconds(4, self.start_text_fade_out)

    def _on_opacity_update(self, value, user_data):
        self.welcome_label.set_opacity(value)

    def start_text_fade_out(self):
        target = Adw.CallbackAnimationTarget.new(self._on_opacity_update, None)
        animation = Adw.TimedAnimation.new(
            self.welcome_label, 1.0, 0.0, 500, target
        )
        animation.connect("done", self.change_text_and_fade_in)
        animation.play()
        return True

    def change_text_and_fade_in(self, animation):
        self.current_lang_index = (self.current_lang_index + 1) % len(self.translations)
        
        # Update welcome label
        new_text = self.translations[self.current_lang_index]
        self.welcome_label.set_markup(f'<span weight="bold">{new_text}</span>')

        # **NEW:** Update the button's label using the same index.
        new_button_text = self.button_translations[self.current_lang_index]
        self.btn_install.set_label(new_button_text)

        # Fade in the welcome label
        target = Adw.CallbackAnimationTarget.new(self._on_opacity_update, None)
        fade_in_animation = Adw.TimedAnimation.new(
            self.welcome_label, 0.0, 1.0, 500, target
        )
        fade_in_animation.play()

if __name__ == "__main__":
    app = Adw.Application(application_id="com.example.WelcomeApp")
    def on_activate(app):
        win = Adw.ApplicationWindow(application=app)
        win.set_title("Welcome Page")
        welcome_widget = WelcomeWidget()
        win.set_content(welcome_widget)
        win.present()
    app.connect('activate', on_activate)
    app.run(None)