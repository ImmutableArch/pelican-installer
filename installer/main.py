#!/usr/bin/env python3
import sys
import signal
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from installer.pages.language_select import LanguageSelectPage
from installer.pages.welcome import WelcomePage
from installer.pages.timezone_select import TimezoneSelectPage
from installer.pages.keyborard_select import KeyboardLayoutPage
from installer.pages.disk_managent import DiskManagent
from installer.pages.user_creation import UserAccountPage
from installer.pages.installation_page import InstallationPage

Adw.init()



class PelicanInstallerApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.pelican.installer",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.connect("activate", self.on_activate)
        # INSTALATION DATA
        self.selected_language = None
        self.installation_mode = None   # 'auto' lub 'manual'
        self.selected_disk = None       # np. '/dev/sda'
        self.selected_layout = None
        self.selected_timezone = None

    def on_activate(self, app):
        # główne okno
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("Pelican Installer 🪶")
        self.window.set_default_size(1280, 720)
        self.window.fullscreen()
        self.window.set_decorated(False)
        self.window.connect("close-request", self.on_close_request)

        # styl — Libadwaita API
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        # CSS provider — powiększenie fontów
        css = b"""
        * {
            font-size: 16pt;
        }
        label {
            font-size: 18pt;
        }
        button {
            font-size: 16pt;
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
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(400)  # czas w ms
        self.window.set_content(self.stack)

        # strony
        self.welcome_page = WelcomePage(self)
        self.language_page = LanguageSelectPage(self)
        self.timezone_page = TimezoneSelectPage(self)
        self.keyboard_page = KeyboardLayoutPage(self)
        self.managent_part_page = DiskManagent(self)
        self.user_creation_page = UserAccountPage(self)
        self.installation_page = InstallationPage(self)

        self.stack.add_named(self.welcome_page, "welcome")
        self.stack.add_named(self.language_page, "language")
        self.stack.add_named(self.timezone_page, "timezone")
        self.stack.add_named(self.keyboard_page, "keyboard")
        #self.stack.add_named(self.user_creation_page, "user")
        self.stack.add_named(self.managent_part_page, "disk_managent")
        self.stack.add_named(self.user_creation_page, "user")
        self.stack.add_named(self.installation_page, "install")

        self.stack.set_visible_child_name("welcome")
        self.window.present()

    def go_to(self, page_name: str):
        """Przełączanie stron"""
        self.stack.set_visible_child_name(page_name)

    def on_close_request(self, *args):
        """Zamknięcie aplikacji (np. przy zamykaniu okna)"""
        print("[Pelican Installer] Closing gracefully...")
        self.quit()
        return False  # False = pozwól GTK zamknąć okno

    # Kiedy użytkownik kliknie "Begin installation"
    def on_begin_installation(self):
        self.go_to("install")
        self.installation_page.start_installation()



def main():
    app = PelicanInstallerApp()

    # Obsługa sygnałów — zamknięcie aplikacji w GTK4
    import signal
    signal.signal(signal.SIGINT, lambda s, f: app.quit())    # Ctrl+C
    signal.signal(signal.SIGTERM, lambda s, f: app.quit())   # kill
    # Ctrl+Z (SIGTSTP) można obsłużyć, ale terminal zwykle wstrzymuje proces
    signal.signal(signal.SIGTSTP, lambda s, f: app.quit())

    try:
        return app.run(sys.argv)
    except KeyboardInterrupt:
        print("\n[Pelican Installer] Interrupted by user (Ctrl+C)")
        return 0



if __name__ == "__main__":
    raise SystemExit(main())
