import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class WelcomePage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app

        # Layout główny
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        box.set_margin_top(100)
        box.set_margin_bottom(100)
        box.set_margin_start(80)
        box.set_margin_end(80)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        self.set_child(box)

        title = Gtk.Label(label="🐧 <big><b>Welcome to Pelican Installer</b></big>", use_markup=True)
        title.set_halign(Gtk.Align.CENTER)
        box.append(title)

        subtitle = Gtk.Label(label="Let’s set up your Arch-CoreOS system quickly and safely 🪶")
        subtitle.set_halign(Gtk.Align.CENTER)
        box.append(subtitle)

        btn_continue = Gtk.Button(label="Continue →")
        btn_continue.add_css_class("suggested-action")
        btn_continue.set_halign(Gtk.Align.CENTER)
        btn_continue.connect("clicked", self.on_continue)
        box.append(btn_continue)

    def on_continue(self, button):
        self.app.go_to("language")
