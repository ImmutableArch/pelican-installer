#!/usr/bin/env python3
import gi
import re

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject


class UserAccountPage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.set_child(self._build_ui())

    # -------------------------
    # Build UI
    # -------------------------
    def _build_ui(self):
        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            margin_top=30,
            margin_bottom=30,
            margin_start=40,
            margin_end=40,
        )
        outer.set_hexpand(True)
        outer.set_vexpand(True)

        title = Gtk.Label()
        title.set_markup("<big><b>Create User Account</b></big>")
        title.set_halign(Gtk.Align.CENTER)
        outer.append(title)

        subtitle = Gtk.Label(
            label="Set your name, username, and password. The installer will use this account for login."
        )
        subtitle.add_css_class("dim-label")
        subtitle.set_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)
        outer.append(subtitle)

        # Form area
        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.FILL)
        grid.set_vexpand(True)
        outer.append(grid)

        # Full name
        grid.attach(Gtk.Label(label="Full Name:"), 0, 0, 1, 1)
        self.entry_fullname = Gtk.Entry(placeholder_text="John Doe")
        self.entry_fullname.set_hexpand(True)
        grid.attach(self.entry_fullname, 1, 0, 1, 1)

        # Username
        grid.attach(Gtk.Label(label="Username:"), 0, 1, 1, 1)
        self.entry_username = Gtk.Entry(placeholder_text="johndoe")
        self.entry_username.set_hexpand(True)
        grid.attach(self.entry_username, 1, 1, 1, 1)

        # Password
        grid.attach(Gtk.Label(label="Password:"), 0, 2, 1, 1)
        self.entry_password = Gtk.PasswordEntry(placeholder_text="Enter password")
        self.entry_password.set_hexpand(True)
        grid.attach(self.entry_password, 1, 2, 1, 1)

        # Password confirmation
        grid.attach(Gtk.Label(label="Confirm Password:"), 0, 3, 1, 1)
        self.entry_confirm = Gtk.PasswordEntry(placeholder_text="Re-enter password")
        self.entry_confirm.set_hexpand(True)
        grid.attach(self.entry_confirm, 1, 3, 1, 1)

        # Password strength indicator
        self.strength_label = Gtk.Label(label="Password strength: ")
        self.strength_label.set_halign(Gtk.Align.START)
        grid.attach(self.strength_label, 1, 4, 1, 1)

        # Error label (validation feedback)
        self.error_label = Gtk.Label()
        self.error_label.add_css_class("error")
        self.error_label.set_wrap(True)
        self.error_label.set_halign(Gtk.Align.CENTER)
        outer.append(self.error_label)

        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_box.set_halign(Gtk.Align.CENTER)
        outer.append(nav_box)

        self.btn_back = Gtk.Button(label="← Back")
        self.btn_proceed = Gtk.Button(label="Install")
        self.btn_proceed.set_sensitive(False)
        nav_box.append(self.btn_back)
        nav_box.append(self.btn_proceed)

        self.btn_back.connect("clicked", self._on_back)
        self.btn_proceed.connect("clicked", self._on_proceed)

        # Live validation signals
        for entry in [self.entry_fullname, self.entry_username, self.entry_password, self.entry_confirm]:
            entry.connect("changed", self._validate_inputs)

        return outer

    # -------------------------
    # Validation logic
    # -------------------------
    def _validate_inputs(self, *_):
        fullname = self.entry_fullname.get_text().strip()
        username = self.entry_username.get_text().strip()
        password = self.entry_password.get_text()
        confirm = self.entry_confirm.get_text()

        # Username validation
        if not username:
            self._set_error("Username cannot be empty.")
            return self._disable_continue()

        if not re.match(r"^[a-z_][a-z0-9_-]*[$]?$", username):
            self._set_error("Username contains invalid characters. Use lowercase letters, digits, '-', or '_'.")
            return self._disable_continue()

        # Password checks
        if len(password) < 6:
            self._set_error("Password is too short (minimum 6 characters).")
            self._update_strength(password)
            return self._disable_continue()

        if password != confirm:
            self._set_error("Passwords do not match.")
            self._update_strength(password)
            return self._disable_continue()

        # Update strength display
        strength = self._update_strength(password)
        self._set_error("")  # clear

        # Enable button only if all valid
        if fullname and username and password and confirm and strength != "Weak":
            self.btn_proceed.set_sensitive(True)
        else:
            self._disable_continue()

    def _update_strength(self, password):
        """Simple strength estimator"""
        if not password:
            self.strength_label.set_text("Password strength: —")
            return "None"

        score = 0
        if len(password) >= 8:
            score += 1
        if re.search(r"[A-Z]", password):
            score += 1
        if re.search(r"[0-9]", password):
            score += 1
        if re.search(r"[^A-Za-z0-9]", password):
            score += 1

        if score <= 1:
            level = "Weak"
        elif score == 2:
            level = "Medium"
        else:
            level = "Strong"

        self.strength_label.set_text(f"Password strength: {level}")
        return level

    def _set_error(self, message):
        self.error_label.set_text(message)

    def _disable_continue(self):
        self.btn_proceed.set_sensitive(False)

    # -------------------------
    # Navigation
    # -------------------------
    def _on_back(self, button):
        if hasattr(self.app, "go_to"):
            self.app.go_to("disk_managent")

    def _on_proceed(self, button):
        user_data = {
            "full_name": self.entry_fullname.get_text().strip(),
            "username": self.entry_username.get_text().strip(),
            "password": '*' * len(self.entry_password.get_text()),
        }

        print("[UserAccountPage] User configuration:", user_data)
        setattr(self.app, "user_account_data", user_data)
        setattr(self.app, "installation_mode", "manual")

        self.app.on_begin_installation()
