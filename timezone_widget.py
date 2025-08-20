#!/usr/bin/env python3

import gi
import subprocess

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, GObject
from simple_localization_manager import get_localization_manager


class TimezoneWidget(Gtk.Box):
    """
    A GTK widget for selecting a system timezone, with timezones
    grouped by continent in expandable rows.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(20)
        self.set_margin_top(30)
        self.set_margin_bottom(30)

        # A list to hold the top-level expander rows for filtering
        self.expander_rows = []
        self.selected_row = None

        # --- Title Label ---
        self.title = Gtk.Label()
        self.title.set_markup('<span size="xx-large" weight="bold">Select Your Timezone</span>')
        self.title.set_halign(Gtk.Align.CENTER)
        self.append(self.title)

        # --- Adw.Clamp constrains the width of the content ---
        clamp = Adw.Clamp(margin_start=12, margin_end=12, maximum_size=600)
        clamp.set_vexpand(True)
        self.append(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        clamp.set_child(content_box)

        # --- Subtitle Label ---
        self.subtitle = Gtk.Label(
            label="Choose a city in your region. This will be used to set the clock.",
            halign=Gtk.Align.CENTER
        )
        self.subtitle.add_css_class('dim-label')
        content_box.append(self.subtitle)

        # --- Search Entry ---
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search for your city or region...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        content_box.append(self.search_entry)

        # --- Scrolled Window for the List ---
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_has_frame(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        content_box.append(scrolled_window)

        # --- ListBox to display each timezone ---
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.get_style_context().add_class("boxed-list")
        scrolled_window.set_child(self.list_box)
        
        # Populate the list with available timezones
        self.populate_timezones()

        # --- Bottom Navigation Buttons ---
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        self.append(button_box)

        self.btn_back = Gtk.Button(label="Back")
        self.btn_back.add_css_class('buttons_all')
        button_box.append(self.btn_back)

        self.btn_proceed = Gtk.Button(label="Continue")
        self.btn_proceed.add_css_class('suggested-action')
        self.btn_proceed.add_css_class('buttons_all')
        self.btn_proceed.set_sensitive(False) # Disabled until a selection is made
        self.btn_proceed.connect("clicked", self.on_continue_clicked)
        button_box.append(self.btn_proceed)

    def populate_timezones(self):
        """Fetches timezones, groups them by continent, and populates the list."""
        try:
            result = subprocess.run(
                ['timedatectl', 'list-timezones'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            timezones = result.stdout.strip().split('\n')
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error getting timezones: {e}. Using a fallback list.")
            timezones = ["UTC", "America/New_York", "Europe/London", "Europe/Warsaw", "Asia/Tokyo", "Australia/Sydney"]
        
        # --- Group timezones by continent ---
        grouped_timezones = {}
        for tz in timezones:
            if "/" in tz:
                continent = tz.split('/')[0]
                if continent not in grouped_timezones:
                    grouped_timezones[continent] = []
                grouped_timezones[continent].append(tz)
            else: # For timezones like 'UTC'
                if "Other" not in grouped_timezones:
                    grouped_timezones["Other"] = []
                grouped_timezones["Other"].append(tz)

        # --- Populate the list with expandable rows ---
        for continent in sorted(grouped_timezones.keys()):
            expander = Adw.ExpanderRow(title=continent)
            self.list_box.append(expander)

            nested_list_box = Gtk.ListBox()
            nested_list_box.get_style_context().add_class("boxed-list")
            nested_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
            nested_list_box.connect("row-selected", self.on_row_selected)
            expander.add_row(nested_list_box)
            
            expander.child_rows = []
            for tz_name in sorted(grouped_timezones[continent]):
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=tz_name, xalign=0, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
                row.set_child(label)
                
                row.timezone_name = tz_name
                row.search_term = tz_name.lower().replace("_", " ")
                
                nested_list_box.append(row)
                expander.child_rows.append(row)
            
            self.expander_rows.append(expander)


    def on_search_changed(self, entry):
        """Filters the list based on user input, showing and expanding relevant groups."""
        search_text = entry.get_text().lower()
        
        for expander in self.expander_rows:
            visible_children = 0
            for row in expander.child_rows:
                is_visible = search_text in row.search_term
                row.set_visible(is_visible)
                if is_visible:
                    visible_children += 1
            
            expander.set_visible(visible_children > 0)
            if search_text:
                expander.set_expanded(visible_children > 0)


    def save_timezone_config(self):
        """Save the selected timezone configuration to /tmp/installer_config/etc/"""
        selected_timezone = self.get_selected_timezone()
        if not selected_timezone:
            return False
        
        try:
            import os
            
            # Create directory structure in /tmp/installer_config/etc/
            etc_dir = "/tmp/installer_config/etc"
            os.makedirs(etc_dir, exist_ok=True)
            
            # Save timezone to a plain text file (like Arch's /etc/timezone)
            timezone_path = os.path.join(etc_dir, "timezone")
            with open(timezone_path, 'w') as f:
                f.write(selected_timezone + '\n')
            
            print(f"Timezone configuration saved to: {timezone_path}")
            
            # Also create a localtime configuration file for the installer to process
            # This file will tell the installer which timezone file to symlink
            localtime_config_path = os.path.join(etc_dir, "localtime.conf")
            with open(localtime_config_path, 'w') as f:
                f.write(f"TIMEZONE={selected_timezone}\n")
                f.write(f"# This file should be used by the installer to create the symlink:\n")
                f.write(f"# ln -sf /usr/share/zoneinfo/{selected_timezone} /etc/localtime\n")
            
            print(f"Localtime configuration saved to: {localtime_config_path}")
            
            # Create an installer script for timezone setup
            self.create_timezone_install_script(selected_timezone)
            
            return True
            
        except Exception as e:
            print(f"Error saving timezone configuration: {e}")
            return False

    def create_timezone_install_script(self, timezone):
        """Create a script that the installer can run to set up the timezone"""
        try:
            import os
            
            # Create the installer config directory if it doesn't exist
            installer_dir = "/tmp/installer_config"
            os.makedirs(installer_dir, exist_ok=True)
            
            script_path = os.path.join(installer_dir, "setup_timezone.sh")
            
            script_content = f"""#!/bin/bash
    # Timezone setup script generated by Linexin Installer
    # Generated timezone: {timezone}

    CHROOT_DIR="${{1:-}}"

    if [ -n "$CHROOT_DIR" ]; then
        # If running in chroot environment during installation
        echo "Setting timezone to {timezone} in $CHROOT_DIR"
        
        # Create the symlink for localtime
        ln -sf "/usr/share/zoneinfo/{timezone}" "$CHROOT_DIR/etc/localtime"
        
        # Set the timezone in /etc/timezone (some systems use this)
        echo "{timezone}" > "$CHROOT_DIR/etc/timezone"
        
        # If systemd is available, set timezone there too
        if [ -f "$CHROOT_DIR/usr/bin/timedatectl" ]; then
            chroot "$CHROOT_DIR" timedatectl set-timezone "{timezone}" 2>/dev/null || true
        fi
    else
        # If running on live system
        echo "Setting timezone to {timezone} on current system"
        
        # Create the symlink for localtime
        sudo ln -sf "/usr/share/zoneinfo/{timezone}" /etc/localtime
        
        # Set the timezone in /etc/timezone
        echo "{timezone}" | sudo tee /etc/timezone
        
        # Use timedatectl if available
        if command -v timedatectl &> /dev/null; then
            sudo timedatectl set-timezone "{timezone}"
        fi
    fi

    # Generate /etc/adjtime for hardware clock
    if [ -n "$CHROOT_DIR" ]; then
        echo "0.0 0 0.0" > "$CHROOT_DIR/etc/adjtime"
        echo "0" >> "$CHROOT_DIR/etc/adjtime"
        echo "UTC" >> "$CHROOT_DIR/etc/adjtime"
    else
        echo "0.0 0 0.0" | sudo tee /etc/adjtime
        echo "0" | sudo tee -a /etc/adjtime
        echo "UTC" | sudo tee -a /etc/adjtime
    fi

    echo "Timezone configuration completed successfully!"
    """
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make the script executable
            os.chmod(script_path, 0o755)
            
            print(f"Timezone setup script created at: {script_path}")
            return True
            
        except Exception as e:
            print(f"Error creating timezone setup script: {e}")
            return False

    def on_row_selected(self, listbox, row):
        """Updated to save timezone config when a timezone is selected"""
        if self.selected_row and self.selected_row != row:
            if self.selected_row.get_parent() != listbox:
                self.selected_row.get_parent().unselect_row(self.selected_row)

        self.selected_row = row
        self.btn_proceed.set_sensitive(row is not None)
        
        # Save timezone configuration when a timezone is selected
        if row is not None:
            self.save_timezone_config()


    def get_timezone_config_path(self):
        """Get the path to the generated timezone configuration file"""
        return "/tmp/installer_config/etc/timezone"

    def on_continue_clicked(self, button):
        """Handle the Continue button click"""
        if self.save_timezone_config():
            selected_tz = self.get_selected_timezone()
            print(f"Timezone configuration saved for: {selected_tz}")
            # You can add navigation to the next widget here
        else:
            print("Failed to save timezone configuration")

    def get_selected_timezone(self):
        """Public method to get the selected timezone string."""
        if self.selected_row:
            return self.selected_row.timezone_name
        return None
