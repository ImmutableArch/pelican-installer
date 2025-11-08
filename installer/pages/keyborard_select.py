import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class KeyboardLayoutPage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.selected_layout = None

        # --- Main layout ---
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_valign(Gtk.Align.FILL)
        main_box.set_halign(Gtk.Align.FILL)
        self.set_child(main_box)

        title = Gtk.Label(label="⌨️ <big><b>Select Keyboard Layout</b></big>", use_markup=True)
        title.set_halign(Gtk.Align.CENTER)
        main_box.append(title)

        # --- Keyboard layouts container ---
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        main_box.append(scrolled)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.set_child(self.listbox)

        # --- Load and group keyboard layouts ---
        layouts = self.get_available_layouts()
        grouped_layouts = self.group_layouts(layouts)
        self.populate_layouts(grouped_layouts)

        # --- Buttons ---
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        btn_box.set_halign(Gtk.Align.CENTER)
        main_box.append(btn_box)

        btn_back = Gtk.Button(label="← Back")
        btn_back.connect("clicked", self.on_back)
        btn_box.append(btn_back)

        self.btn_next = Gtk.Button(label="Next →")
        self.btn_next.add_css_class("suggested-action")
        self.btn_next.set_sensitive(False)
        self.btn_next.connect("clicked", self.on_next)
        btn_box.append(self.btn_next)

    # ----------------------------
    # Load keymaps from system
    # ----------------------------
    def get_available_layouts(self):
        """Read available keyboard layouts from XKB symbols."""
        keymaps_dir = "/usr/share/X11/xkb/symbols"
        keymaps = []

        if os.path.isdir(keymaps_dir):
            for f in sorted(os.listdir(keymaps_dir)):
                if f.isalpha():
                    keymaps.append(f)

        # Add ergonomic / special ones manually
        keymaps += ["dvorak", "colemak"]
        return keymaps

    # ----------------------------
    # Grouping logic (your code)
    # ----------------------------
    def group_layouts(self, keymaps):
        groups = {
            "English": [], "German": [], "French": [], "Spanish": [], "Russian": [],
            "Portuguese": [], "Polish": [], "Italian": [], "Swedish": [], "Norwegian": [],
            "Danish": [], "Finnish": [], "Dutch": [], "Czech": [], "Slovak": [],
            "Hungarian": [], "Romanian": [], "Bulgarian": [], "Greek": [],
            "Turkish": [], "Ukrainian": [], "Serbian": [], "Croatian": [], "Slovenian": [],
            "Ergonomic / Special": [], "Other": []
        }

        prefix_map = {
            'us': "English", 'gb': "English", 'uk': "English", 'ie': "English",
            'de': "German",
            'fr': "French", 'be': "French", 'ca': "French",
            'es': "Spanish", 'la-latin1': "Spanish",
            'ru': "Russian",
            'pt': "Portuguese", 'br': "Portuguese",
            'pl': "Polish",
            'it': "Italian",
            'sv': "Swedish", 'se': "Swedish",
            'no': "Norwegian",
            'dk': "Danish",
            'fi': "Finnish",
            'nl': "Dutch",
            'cz': "Czech",
            'sk': "Slovak",
            'hu': "Hungarian",
            'ro': "Romanian",
            'bg': "Bulgarian",
            'gr': "Greek",
            'tr': "Turkish",
            'ua': "Ukrainian", 'by': "Ukrainian",
            'sr': "Serbian", 'rs': "Serbian",
            'hr': "Croatian", 'croat': "Croatian",
            'slovene': "Slovenian", 'si': "Slovenian",
            'dvorak': "Ergonomic / Special", 'colemak': "Ergonomic / Special",
        }

        for keymap in keymaps:
            found = False
            if len(keymap) >= 2:
                prefix_2 = keymap[:2]
                if prefix_2 in prefix_map:
                    groups[prefix_map[prefix_2]].append(keymap)
                    continue

            for prefix, group_name in prefix_map.items():
                if keymap.startswith(prefix):
                    groups[group_name].append(keymap)
                    found = True
                    break

            if not found:
                groups["Other"].append(keymap)

        return {k: sorted(v) for k, v in sorted(groups.items()) if v}

    # ----------------------------
    # GUI population
    # ----------------------------
    def populate_layouts(self, grouped):
        for group_name, layouts in grouped.items():
            expander = Adw.ExpanderRow(title=group_name)
            for layout in layouts:
                row = Gtk.ListBoxRow()
                button = Gtk.Button(label=layout)
                button.connect("clicked", self.on_layout_selected, layout)
                row.set_child(button)
                expander.add_row(row)
            self.listbox.append(expander)

    # ----------------------------
    # Event handlers
    # ----------------------------
    def on_layout_selected(self, button, layout):
        self.selected_layout = layout
        print(f"[Pelican Installer] Selected layout: {layout}")
        self.btn_next.set_sensitive(True)

    def on_back(self, button):
        if hasattr(self.app, 'go_to'):
            self.app.go_to("timezone")

    def on_next(self, button):
        if self.selected_layout:
            if hasattr(self.app, 'selected_layout'):
                self.app.selected_layout = self.selected_layout
            print(f"[Pelican Installer] Proceeding with layout: {self.selected_layout}")
            self.app.go_to("disk_managent")
            #self.app.go_to("user")
        else:
            print("[Pelican Installer] Please select a keyboard layout first.")
