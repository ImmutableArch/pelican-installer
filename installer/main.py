#!/usr/bin/env python3
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from installer.pages.language_select import LanguageSelectPage
from installer.pages.welcome import WelcomePage
from installer.pages.timezone_select import TimezoneSelectPage

Adw.init()

class PelicanInstallerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.pelican.installer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)
        self.selected_language = None

    def on_activate(self, app):
        # główne okno
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("Pelican Installer 🪶")
        self.window.set_default_size(1280, 720)
        self.window.fullscreen()
        self.window.set_decorated(False)

        # styl — Libadwaita API
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

         # CSS provider — powiększenie fontów
        css = b"""
        * {
            font-size: 18pt;
        }
        label {
            font-size: 22pt;
        }
        button {
            font-size: 18pt;
            padding: 10px 25px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            self.window.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # główny stack
        self.stack = Gtk.Stack()
        self.window.set_content(self.stack)

        # strony
        self.welcome_page = WelcomePage(self)
        self.language_page = LanguageSelectPage(self)
        self.timezone_page = TimezoneSelectPage(self)

        self.stack.add_named(self.welcome_page, "welcome")
        self.stack.add_named(self.language_page, "language")
        self.stack.add_named(self.timezone_page, "timezone")

        self.stack.set_visible_child_name("welcome")
        self.window.present()

    def go_to(self, page_name: str):
        """Przełączanie stron"""
        self.stack.set_visible_child_name(page_name)

def main():
    app = PelicanInstallerApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    raise SystemExit(main())
