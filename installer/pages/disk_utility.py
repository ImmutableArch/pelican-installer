#!/usr/bin/env python3
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class DiskUtilityPage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.selection = None  # 'auto' lub 'manual'

        # --- główny układ ---
        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=30,
            margin_top=60,
            margin_bottom=60,
            margin_start=80,
            margin_end=80,
        )
        vbox.set_valign(Gtk.Align.CENTER)
        vbox.set_halign(Gtk.Align.CENTER)
        self.set_child(vbox)

        # --- tytuł ---
        title = Gtk.Label(label="<big><b>🪶 Disk Setup</b></big>", use_markup=True)
        title.set_halign(Gtk.Align.CENTER)
        vbox.append(title)

        subtitle = Gtk.Label(
            label="Please choose how you want to set up your disk partitions."
        )
        subtitle.set_halign(Gtk.Align.CENTER)
        vbox.append(subtitle)

        # --- grupa wyboru (ładny Adwaita styl) ---
        group = Adw.PreferencesGroup(title="Partitioning mode")

        self.auto_row = Adw.ActionRow(
            title="Automatic Partitioning",
            subtitle="Erase the entire disk and install automatically",
        )
        self.manual_row = Adw.ActionRow(
            title="Manual Partitioning",
            subtitle="Choose and create partitions yourself",
        )

        self.auto_button = Gtk.CheckButton()
        self.manual_button = Gtk.CheckButton()

        # Radio-like behavior
        self.auto_button.set_group(self.manual_button)

        self.auto_button.connect("toggled", self.on_selection_changed, "auto")
        self.manual_button.connect("toggled", self.on_selection_changed, "manual")

        self.auto_row.add_suffix(self.auto_button)
        self.manual_row.add_suffix(self.manual_button)

        self.auto_row.set_activatable_widget(self.auto_button)
        self.manual_row.set_activatable_widget(self.manual_button)

        group.add(self.auto_row)
        group.add(self.manual_row)

        vbox.append(group)

        # --- przyciski nawigacji ---
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        nav_box.set_halign(Gtk.Align.CENTER)
        vbox.append(nav_box)

        self.btn_back = Gtk.Button(label="← Back")
        self.btn_back.connect("clicked", self.on_back)
        nav_box.append(self.btn_back)

        self.btn_next = Gtk.Button(label="Next →")
        self.btn_next.set_sensitive(False)
        self.btn_next.connect("clicked", self.on_next)
        nav_box.append(self.btn_next)

    # --- zmiana wyboru ---
    def on_selection_changed(self, button, mode):
        if button.get_active():
            self.selection = mode
            self.btn_next.set_sensitive(True)
            print(f"[Pelican Installer] Selected mode: {mode}")

    # --- przycisk cofania ---
    def on_back(self, button):
        self.app.go_to("keyboard")

    # --- przycisk dalej ---
    def on_next(self, button):
        if not self.selection:
            return

        if self.selection == "auto":
            print("[Pelican Installer] Proceeding to automatic partitioning...")
            self.app.go_to("auto_partition")
        else:
            print("[Pelican Installer] Proceeding to manual partitioning...")
            self.app.go_to("manual_partition")
