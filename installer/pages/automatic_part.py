#!/usr/bin/env python3
# installer/pages/automatic_part.py
"""
Automatic partitioning page for Pelican Installer.

- detects disks (lsblk -J, fallback /sys/block)
- shows disks as rows with CheckButtons (single-select enforced manually)
- confirms destructive action with a Gtk.Dialog created WITHOUT kwargs
"""

import gi
import subprocess
import json
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Optional helper - may be absent in some environments
try:
    from installer.disk_utils import DiskUtils
except Exception:
    DiskUtils = None


class AutoPartitionPage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.selected_disk = None
        self.disk_rows = []  # list of tuples (row_widget, check_button)
        self._suppress_toggle = False
        self.map_file_path = None

        # Main container (centered but not full-width)
        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=30,
            margin_top=40,
            margin_bottom=40,
            margin_start=60,
            margin_end=60,
        )
        vbox.set_valign(Gtk.Align.CENTER)
        vbox.set_halign(Gtk.Align.CENTER)
        self.set_child(vbox)

        # Title and subtitle
        title = Gtk.Label(label="<big><b>🧠 Automatic Partitioning</b></big>", use_markup=True)
        title.set_halign(Gtk.Align.CENTER)
        vbox.append(title)

        subtitle = Gtk.Label(label="Select the disk where Pelican OS will be installed.")
        subtitle.set_halign(Gtk.Align.CENTER)
        vbox.append(subtitle)

        # Preferences group to hold disk rows
        self.disk_group = Adw.PreferencesGroup(title="Available Disks")
        vbox.append(self.disk_group)

        # Navigation buttons
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

        # Populate disk list
        self.populate_disks()

    # -------------------------
    # Disk detection and UI
    # -------------------------
    def clear_disk_group(self):
        """Remove previous children from the preferences group (defensive)."""
        try:
            children = list(self.disk_group.get_children())
            for c in children:
                try:
                    self.disk_group.remove(c)
                except Exception:
                    try:
                        c.unparent()
                    except Exception:
                        pass
        except Exception:
            pass

    def populate_disks(self):
        """
        Detect block devices and populate the UI.
        Prefer `lsblk -J`, fallback to scanning /sys/block.
        """
        self.clear_disk_group()
        self.disk_rows = []
        devices = []

        # Try lsblk -J (JSON) to get name, size, model, type
        try:
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,SIZE,MODEL,TYPE"],
                capture_output=True, text=True, check=True
            )
            print("[Pelican Installer] lsblk -J output:")
            print(result.stdout)
            data = json.loads(result.stdout)

            def gather(blocks):
                for b in blocks:
                    if b.get("type") == "disk":
                        devices.append({
                            "name": b.get("name"),
                            "size": b.get("size") or "Unknown",
                            "model": b.get("model") or "Unknown",
                            "type": "disk",
                        })
                    # Also recurse children (defensive)
                    if b.get("children"):
                        gather(b.get("children"))

            if "blockdevices" in data:
                gather(data["blockdevices"])
        except subprocess.CalledProcessError as e:
            print(f"[Pelican Installer] lsblk failed: {e}; stdout:{getattr(e,'stdout','')}; stderr:{getattr(e,'stderr','')}")
        except Exception as e:
            print(f"[Pelican Installer] lsblk parse error: {e}")

        # Fallback: scan /sys/block if nothing from lsblk
        if not devices:
            try:
                print("[Pelican Installer] Falling back to /sys/block scan")
                for entry in sorted(os.listdir("/sys/block")):
                    if entry.startswith(("loop", "ram", "zram", "dm-")):
                        continue
                    devices.append({
                        "name": entry,
                        "size": "Unknown",
                        "model": "Unknown",
                        "type": "disk",
                    })
                print(f"[Pelican Installer] /sys/block candidates: {', '.join(d['name'] for d in devices)}")
            except Exception as e:
                print(f"[Pelican Installer] /sys/block fallback failed: {e}")

        if not devices:
            # nothing found
            label = Gtk.Label(label="No disks detected.")
            self.disk_group.add(label)
            return

        # Build rows: use CheckButton + enforce single selection manually
        found_any = False
        for dev in devices:
            name = dev.get("name")
            size = dev.get("size", "Unknown")
            model = dev.get("model", "Unknown")
            dtype = dev.get("type", "disk")

            if dtype != "disk":
                continue

            device_path = f"/dev/{name}"
            found_any = True

            row = Adw.ActionRow(title=device_path, subtitle=f"{model.strip()} — {size}")

            # Use CheckButton and manually ensure exclusivity in handler
            check = Gtk.CheckButton()
            check.set_hexpand(False)
            check.connect("toggled", self._on_disk_toggled, device_path)

            # Add suffix and make activatable
            row.add_suffix(check)
            row.set_activatable_widget(check)

            try:
                self.disk_group.add(row)
            except Exception:
                # fallback additions
                try:
                    self.disk_group.append(row)
                except Exception:
                    try:
                        self.disk_group.add(row)
                    except Exception:
                        pass

            self.disk_rows.append((row, check))

        if not found_any:
            self.disk_group.add(Gtk.Label(label="No suitable disks found."))

    # -------------------------
    # Selection management
    # -------------------------
    def _on_disk_toggled(self, button, disk_path):
        """
        Enforce single selection: when a check becomes active,
        uncheck all others. Use suppression flag to avoid recursion.
        """
        if getattr(self, "_suppress_toggle", False):
            return

        if button.get_active():
            self._suppress_toggle = True
            try:
                for (r, b) in self.disk_rows:
                    if b is not button:
                        try:
                            b.set_active(False)
                        except Exception:
                            try:
                                b.set_active(False)
                            except Exception:
                                pass
                self.selected_disk = disk_path
                self.btn_next.set_sensitive(True)
                print(f"[Pelican Installer] Selected disk: {disk_path}")
            finally:
                self._suppress_toggle = False
        else:
            # If user unchecked the active one, detect if none remains active
            any_active = False
            for (r, b) in self.disk_rows:
                try:
                    if b.get_active():
                        any_active = True
                        break
                except Exception:
                    pass
            if not any_active:
                self.selected_disk = None
                self.btn_next.set_sensitive(False)
                print("[Pelican Installer] No disk selected")

    # -------------------------
    # Navigation and destructive dialog (Gtk.Dialog without kwargs)
    # -------------------------
    def on_back(self, button):
        if hasattr(self.app, "go_to"):
            # adapt page name to your app routing if needed
            self.app.go_to("disk")
        else:
            print("[Pelican Installer] Back pressed")

    def on_next(self, button):
        """Create and present a Gtk.Dialog WITHOUT kwargs (defensive)."""
        if not self.selected_disk:
            return

        # Find a transient parent if possible
        win = None
        try:
            root = None
            if hasattr(self, "get_root"):
                try:
                    root = self.get_root()
                except Exception:
                    root = None

            if isinstance(root, Gtk.Window):
                win = root
            elif hasattr(self.app, "window") and isinstance(self.app.window, Gtk.Window):
                win = self.app.window
            else:
                # Try application's active window as last resort
                try:
                    get_aw = getattr(self.app, "get_active_window", None)
                    if callable(get_aw):
                        aw = get_aw()
                        if isinstance(aw, Gtk.Window):
                            win = aw
                except Exception:
                    win = None
        except Exception:
            win = None

        # Create Gtk.Dialog without kwargs
        dialog = Gtk.Dialog()
        try:
            # transient_for only if we have a real Gtk.Window
            if isinstance(win, Gtk.Window):
                try:
                    dialog.set_transient_for(win)
                except Exception:
                    pass

            dialog.set_modal(True)

            # Add buttons (no kwargs)
            # Use CANCEL for safe default and OK for destructive confirm
            cancel_btn = dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            erase_btn = dialog.add_button("Erase & Install", Gtk.ResponseType.OK)

            # Optionally set default response (Cancel)
            try:
                dialog.set_default_response(Gtk.ResponseType.CANCEL)
            except Exception:
                pass

            # Content area: message label with markup
            content_area = dialog.get_content_area()
            body = Gtk.Label()
            body.set_halign(Gtk.Align.START)
            body.set_valign(Gtk.Align.CENTER)
            body.set_margin_top(12)
            body.set_margin_bottom(12)
            body.set_margin_start(12)
            body.set_margin_end(12)
            # Use markup to bold the disk name
            body.set_markup(
                f"All data on <b>{self.selected_disk}</b> will be permanently erased.\n"
                "This action cannot be undone.\n\nDo you want to continue?"
            )

            # Append label to dialog content area (Gtk 4 API)
            try:
                content_area.append(body)
            except Exception:
                try:
                    content_area.add(body)
                except Exception:
                    try:
                        content_area.pack_start(body, True, True, 0)
                    except Exception:
                        pass

            dialog.connect("response", self.on_erase_response)

            # Present dialog
            try:
                dialog.present()
            except Exception:
                try:
                    dialog.show()
                except Exception:
                    pass

        except Exception as e:
            print(f"[Pelican Installer] Failed to create dialog: {e}")
            try:
                dialog.destroy()
            except Exception:
                pass

    def on_erase_response(self, dialog, response_id):
        """Handle dialog response and destroy dialog safely."""
        try:
            dialog.close()
        except Exception:
            try:
                dialog.destroy()
            except Exception:
                pass

        if response_id == Gtk.ResponseType.OK:
            print(f"[Pelican Installer] ⚠️ Proceeding with automatic partitioning on {self.selected_disk}")
            self.app.instalation_mode = "auto"
            self.app.selected_disk = self.selected_disk
            # TODO: implement actual automatic partitioning here (spawn worker, run script)
        else:
            print("[Pelican Installer] Cancelled automatic partitioning.")
