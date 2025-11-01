#!/usr/bin/env python3
import gi
import subprocess
import json
import os
import tempfile
import time

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib
from ..disk_utils import DiskUtils


class DiskManagent(Adw.Bin):
    FS_CHOICES = ["ext4", "btrfs", "xfs", "f2fs", "vfat", "ntfs", "exfat", "swap"]
    SIZE_UNITS = ["MB", "GB", "TB"]

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.partition_rows = []
        self.selected_row = None
        self.partition_config = {}
        self.btrfs_subvolumes = {
            '@': '/',
            '@home': '/home',
            '@var': '/var',
            '@tmp': '/tmp',
            '@snapshots': '/.snapshots'
        }
        self.init_partition_config()
        self.set_child(self._build_ui())

    def _build_ui(self):
        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=20,
            margin_bottom=20,
            margin_start=20,
            margin_end=20,
        )
        outer.set_hexpand(True)
        outer.set_vexpand(True)

        title = Gtk.Label()
        title.set_markup("<big><b>Manual Partitioning</b></big>")
        title.set_halign(Gtk.Align.CENTER)
        outer.append(title)

        subtitle = Gtk.Label(
            label="Select a disk and edit partitions. Assign mount points and filesystems."
        )
        subtitle.add_css_class("dim-label")
        subtitle.set_halign(Gtk.Align.CENTER)
        outer.append(subtitle)

        # Disk selector
        self.disk_combo = Gtk.ComboBoxText.new()
        self.disk_combo.set_hexpand(True)
        self.disk_combo.connect("changed", self._on_disk_selected)
        outer.append(self.disk_combo)

        self.disk_info_label = Gtk.Label()
        self.disk_info_label.set_halign(Gtk.Align.START)
        outer.append(self.disk_info_label)

        # Action buttons
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer.append(action_box)

        self.btn_new_table = Gtk.Button(label="New Partition Table")
        self.btn_new_table.connect("clicked", self._on_new_partition_table)
        action_box.append(self.btn_new_table)

        self.btn_auto = Gtk.Button(label="Auto Configure")
        self.btn_auto.connect("clicked", self._on_auto_configure)
        action_box.append(self.btn_auto)

        self.btn_refresh = Gtk.Button(label="Refresh")
        self.btn_refresh.connect("clicked", self._on_refresh)
        action_box.append(self.btn_refresh)

        # Partition management buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer.append(btn_box)
        self.btn_add = Gtk.Button(label="Add Partition")
        self.btn_edit = Gtk.Button(label="Edit Selected")
        self.btn_remove = Gtk.Button(label="Remove Selected")
        self.btn_format = Gtk.Button(label="Format Selected")
        btn_box.append(self.btn_add)
        btn_box.append(self.btn_edit)
        btn_box.append(self.btn_remove)
        btn_box.append(self.btn_format)

        self.btn_add.connect("clicked", self._on_add_partition)
        self.btn_edit.connect("clicked", self._on_edit_partition)
        self.btn_remove.connect("clicked", self._on_remove_partition)
        self.btn_format.connect("clicked", self._on_format_partition)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        outer.append(scrolled)

        self.listbox = Gtk.ListBox.new()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.get_style_context().add_class("boxed-list")
        self.listbox.connect("row-selected", self._on_row_selected)
        scrolled.set_child(self.listbox)

        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_box.set_halign(Gtk.Align.CENTER)
        outer.append(nav_box)
        self.btn_back = Gtk.Button(label="← Back")
        self.btn_proceed = Gtk.Button(label="Continue →")
        self.btn_proceed.add_css_class("suggested-action")
        self.btn_proceed.set_sensitive(False)
        nav_box.append(self.btn_back)
        nav_box.append(self.btn_proceed)
        self.btn_back.connect("clicked", self._on_back)
        self.btn_proceed.connect("clicked", self._on_proceed)

        self._populate_disks()
        return outer

    def _populate_disks(self):
        """Populate disk combo with available disks"""
        try:
            p = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MODEL"],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(p.stdout)
        except Exception as e:
            self._show_error_dialog("Error", f"Error running lsblk: {e}")
            return

        self.disk_combo.remove_all()
        for b in data.get("blockdevices", []):
            if b.get("type") == "disk":
                name = b.get("name")
                size = b.get("size")
                model = b.get("model") or "Unknown"
                self.disk_combo.append_text(f"/dev/{name} — {size} — {model}")

    def _on_disk_selected(self, combo):
        """Handle disk selection"""
        text = combo.get_active_text()
        if not text:
            return
        disk_path = text.split(" ")[0]
        self.disk_info_label.set_text(f"Selected disk: {disk_path}")
        setattr(self.app, "selected_disk", disk_path)
        self.selected_disk = disk_path
        self.populate_partitions_for_disk(disk_path)

    def _on_refresh(self, button):
        """Refresh disk and partition list"""
        self._populate_disks()
        if hasattr(self, 'selected_disk') and self.selected_disk:
            self.populate_partitions_for_disk(self.selected_disk)

    def _detect_boot_mode(self):
        """Detect if the system is running in UEFI or Legacy mode"""
        try:
            if os.path.exists('/sys/firmware/efi'):
                return "uefi"
            else:
                return "legacy"
        except Exception:
            return "legacy"

    def _on_auto_configure(self, button):
        """Auto-configure disk with boot and root partitions"""
        if not hasattr(self, 'selected_disk') or not self.selected_disk:
            self._show_error_dialog("No Selection", "Please select a disk first.")
            return

        boot_mode = self._detect_boot_mode()

        if boot_mode == "uefi":
            message = (f"This will automatically configure {self.selected_disk} for UEFI boot:\n\n"
                      f"• Create GPT partition table\n"
                      f"• Create 512 MiB FAT32 EFI System Partition at /boot/efi\n"
                      f"• Create 1 GiB ext4 boot partition at /boot\n"
                      f"• Create Btrfs root partition at / with remaining space\n"
                      f"  (with subvolumes: @, @home, @var, @tmp, @snapshots)\n\n"
                      f"WARNING: All data on {self.selected_disk} will be lost!")
        else:
            message = (f"This will automatically configure {self.selected_disk} for Legacy boot:\n\n"
                      f"• Create MBR partition table\n"
                      f"• Create 1 GiB ext4 boot partition at /boot (bootable)\n"
                      f"• Create Btrfs root partition at / with remaining space\n"
                      f"  (with subvolumes: @, @home, @var, @tmp, @snapshots)\n\n"
                      f"WARNING: All data on {self.selected_disk} will be lost!")

        dialog = Adw.MessageDialog(
            heading="Auto Configure Disk",
            body=message,
            transient_for=self.get_root()
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("proceed", "Proceed")
        dialog.set_response_appearance("proceed", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_auto_configure_response)
        dialog.present()

    def _on_auto_configure_response(self, dialog, response_id):
        """Handle auto-configure response"""
        if response_id == "proceed":
            self._execute_auto_configure()

    def _execute_auto_configure(self):
        """Execute automatic disk configuration"""
        try:
            boot_mode = self._detect_boot_mode()
            progress_dialog = self._show_progress_dialog(
                "Configuring Disk",
                f"Setting up {boot_mode.upper()} boot configuration..."
            )

            disk = self.selected_disk

            # Create partition table
            if boot_mode == "uefi":
                cmd = ['sudo', 'parted', '-s', disk, 'mklabel', 'gpt']
            else:
                cmd = ['sudo', 'parted', '-s', disk, 'mklabel', 'msdos']

            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if process.returncode != 0:
                raise Exception(f"Failed to create partition table: {process.stderr}")

            time.sleep(1)

            if boot_mode == "uefi":
                # Create EFI partition (512MB)
                cmd = ['sudo', 'parted', '-s', disk, 'mkpart', 'primary', 'fat32', '1MiB', '513MiB']
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if process.returncode != 0:
                    raise Exception(f"Failed to create EFI partition: {process.stderr}")

                # Create /boot partition (1GB)
                cmd = ['sudo', 'parted', '-s', disk, 'mkpart', 'primary', 'ext4', '513MiB', '1537MiB']
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if process.returncode != 0:
                    raise Exception(f"Failed to create boot partition: {process.stderr}")

                # Create root partition (remaining space)
                cmd = ['sudo', 'parted', '-s', disk, 'mkpart', 'primary', 'btrfs', '1537MiB', '100%']
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if process.returncode != 0:
                    raise Exception(f"Failed to create root partition: {process.stderr}")

                # Set ESP flag on first partition
                cmd = ['sudo', 'parted', '-s', disk, 'set', '1', 'esp', 'on']
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                time.sleep(2)

                # Format partitions
                efi_partition = DiskUtils.get_partition_path(disk, 1)
                boot_partition = DiskUtils.get_partition_path(disk, 2)
                root_partition = DiskUtils.get_partition_path(disk, 3)

                # Format EFI as FAT32
                cmd = ['sudo', 'mkfs.fat', '-F', '32', efi_partition]
                subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)

                # Format /boot as ext4
                cmd = ['sudo', 'mkfs.ext4', '-F', boot_partition]
                subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)

                # Format root as Btrfs
                cmd = ['sudo', 'mkfs.btrfs', '-f', root_partition]
                subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)

                # Create Btrfs subvolumes
                self._create_btrfs_subvolumes(root_partition)

                # Update configuration
                self.partition_config[efi_partition] = {
                    'mountpoint': '/boot/efi',
                    'bootable': True,
                    'fstype': 'vfat'
                }
                self.partition_config[boot_partition] = {
                    'mountpoint': '/boot',
                    'bootable': False,
                    'fstype': 'ext4'
                }
                self.partition_config[root_partition] = {
                    'mountpoint': '/',
                    'bootable': False,
                    'fstype': 'btrfs'
                }

            else:  # Legacy mode
                # Create /boot partition (1GB)
                cmd = ['sudo', 'parted', '-s', disk, 'mkpart', 'primary', 'ext4', '1MiB', '1025MiB']
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if process.returncode != 0:
                    raise Exception(f"Failed to create boot partition: {process.stderr}")

                # Create root partition (remaining space)
                cmd = ['sudo', 'parted', '-s', disk, 'mkpart', 'primary', 'btrfs', '1025MiB', '100%']
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if process.returncode != 0:
                    raise Exception(f"Failed to create root partition: {process.stderr}")

                # Set boot flag on first partition
                cmd = ['sudo', 'parted', '-s', disk, 'set', '1', 'boot', 'on']
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                time.sleep(2)

                # Format partitions
                boot_partition = DiskUtils.get_partition_path(disk, 1)
                root_partition = DiskUtils.get_partition_path(disk, 2)

                # Format /boot as ext4
                cmd = ['sudo', 'mkfs.ext4', '-F', boot_partition]
                subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)

                # Format root as Btrfs
                cmd = ['sudo', 'mkfs.btrfs', '-f', root_partition]
                subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)

                # Create Btrfs subvolumes
                self._create_btrfs_subvolumes(root_partition)

                # Update configuration
                self.partition_config[boot_partition] = {
                    'mountpoint': '/boot',
                    'bootable': True,
                    'fstype': 'ext4'
                }
                self.partition_config[root_partition] = {
                    'mountpoint': '/',
                    'bootable': False,
                    'fstype': 'btrfs'
                }

            # Force kernel to re-read partition table
            cmd = ['sudo', 'partprobe', disk]
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            self._save_partition_config()
            self._generate_and_apply_fstab()

            progress_dialog.destroy()
            self._show_info_dialog("Success", f"Disk {disk} configured successfully for {boot_mode.upper()} boot!")
            self._on_refresh(None)

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.destroy()
            self._show_error_dialog("Error", f"Failed to auto-configure: {str(e)}")

    def _on_new_partition_table(self, button):
        """Create new partition table"""
        if not hasattr(self, 'selected_disk') or not self.selected_disk:
            self._show_error_dialog("No Selection", "Please select a disk first.")
            return

        dialog = Adw.MessageDialog(
            heading="Create New Partition Table",
            body=f"This will erase all data on {self.selected_disk}!\n\nSelect partition table type:",
            transient_for=self.get_root()
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("gpt", "GPT (UEFI)")
        dialog.add_response("msdos", "MBR (Legacy)")
        dialog.set_response_appearance("gpt", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_partition_table_response)
        dialog.present()

    def _on_partition_table_response(self, dialog, response_id):
        """Handle partition table creation"""
        if response_id in ["gpt", "msdos"]:
            try:
                table_type = response_id
                cmd = ['sudo', 'parted', '-s', self.selected_disk, 'mklabel', table_type]
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if process.returncode != 0:
                    raise Exception(f"Failed to create partition table: {process.stderr}")

                self._show_info_dialog("Success", f"{table_type.upper()} partition table created on {self.selected_disk}")
                self._on_refresh(None)

            except Exception as e:
                self._show_error_dialog("Error", f"Failed to create partition table: {str(e)}")

    def populate_partitions_for_disk(self, disk):
        """Populate partition list for selected disk"""
        self._clear_list()
        self.partition_rows = []

        try:
            p = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,LABEL,FSTYPE"],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(p.stdout)
        except Exception as e:
            self._add_error_row(f"Error running lsblk: {e}")
            return

        devname = os.path.basename(disk)

        def find_device(blocks, target):
            for b in blocks:
                if b.get("name") == target:
                    return b
                children = b.get("children") or []
                found = find_device(children, target)
                if found:
                    return found
            return None

        disk_entry = find_device(data.get("blockdevices", []), devname)
        if not disk_entry:
            self._add_error_row(f"Disk {disk} not found in lsblk output.")
            return

        children = disk_entry.get("children") or []
        if not children:
            self._add_info_row("No partitions found on this disk.")
            self._update_proceed_sensitive()
            return

        for part in children:
            self._add_partition_row(part)
        self._update_proceed_sensitive()

    def _add_partition_row(self, part):
        """Add partition row to list"""
        pname = part.get("name")
        psize = part.get("size", "")
        pmount = part.get("mountpoint") or ""
        fs = part.get("fstype") or "unknown"
        plabel = part.get("label") or ""

        device_path = f"/dev/{pname}"

        # Get configured mountpoint from our config
        if device_path in self.partition_config:
            pmount = self.partition_config[device_path].get('mountpoint', pmount)
            is_bootable = self.partition_config[device_path].get('bootable', False)
        else:
            is_bootable = False

        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)
        hbox.set_margin_start(6)
        hbox.set_margin_end(6)
        row.set_child(hbox)

        # Icon
        icon = Gtk.Image.new_from_icon_name(
            "emblem-system-symbolic" if is_bootable else "drive-removable-media-symbolic"
        )
        hbox.append(icon)

        label_name = Gtk.Label(label=f"/dev/{pname}", xalign=0)
        label_name.set_width_chars(15)
        label_size = Gtk.Label(label=psize, xalign=0)
        label_size.set_width_chars(10)
        label_mount = Gtk.Label(label=pmount or "(none)", xalign=0)
        label_mount.set_width_chars(15)
        label_fs = Gtk.Label(label=fs, xalign=0)
        label_fs.set_width_chars(10)
        label_label = Gtk.Label(label=plabel, xalign=0)
        label_label.set_width_chars(10)

        hbox.append(label_name)
        hbox.append(label_size)
        hbox.append(label_mount)
        hbox.append(label_fs)
        hbox.append(label_label)

        row.partition_path = device_path
        row.mount_point = pmount
        row.size = psize
        row.fstype = fs
        row.label_text = plabel
        row.is_bootable = is_bootable

        row.size_label = label_size
        row.mount_label = label_mount
        row.fs_label = label_fs
        row.part_label = label_label
        row.icon = icon

        self.listbox.append(row)
        self.partition_rows.append(row)

    def _on_row_selected(self, listbox, row):
        """Handle row selection"""
        self.selected_row = row

    def _on_add_partition(self, button):
        """Add new partition"""
        if not hasattr(self, 'selected_disk') or not self.selected_disk:
            self._show_error_dialog("No Selection", "Please select a disk first.")
            return
        self._show_partition_dialog(is_new=True)

    def _on_edit_partition(self, button):
        """Edit selected partition"""
        if not self.selected_row:
            self._show_error_dialog("No Selection", "Please select a partition first.")
            return
        self._show_partition_dialog(row=self.selected_row)

    def _on_remove_partition(self, button):
        """Remove selected partition"""
        if not self.selected_row:
            self._show_error_dialog("No Selection", "Please select a partition first.")
            return

        dialog = Adw.MessageDialog(
            heading="Remove Partition",
            body=f"Are you sure you want to remove {self.selected_row.partition_path}?\n\nAll data will be lost!",
            transient_for=self.get_root()
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_remove_confirm)
        dialog.present()

    def _on_remove_confirm(self, dialog, response_id):
        """Confirm partition removal"""
        if response_id == "remove":
            self._execute_remove_partition()

    def _execute_remove_partition(self):
        """Execute partition removal"""
        try:
            progress_dialog = self._show_progress_dialog(
                "Removing Partition",
                f"Removing {self.selected_row.partition_path}..."
            )

            disk_info = DiskUtils.parse_disk_path(self.selected_row.partition_path)
            if not disk_info or disk_info['partition_num'] is None:
                raise Exception("Could not determine partition number")

            partition_num = str(disk_info['partition_num'])
            base_disk = disk_info['base_disk']

            cmd = ['sudo', 'parted', '-s', base_disk, 'rm', partition_num]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if process.returncode != 0:
                raise Exception(f"Failed to remove partition: {process.stderr}")

            # Force kernel to re-read partition table
            cmd = ['sudo', 'partprobe', base_disk]
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            # Remove from configuration
            if self.selected_row.partition_path in self.partition_config:
                del self.partition_config[self.selected_row.partition_path]
                self._save_partition_config()
                self._generate_and_apply_fstab()

            progress_dialog.destroy()
            self._show_info_dialog("Success", f"Partition removed successfully")

            time.sleep(1)
            self._on_refresh(None)

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.destroy()
            self._show_error_dialog("Error", f"Failed to remove partition: {str(e)}")

    def _on_format_partition(self, button):
        """Format selected partition"""
        if not self.selected_row:
            self._show_error_dialog("No Selection", "Please select a partition first.")
            return

        dialog = Adw.MessageDialog(
            heading="Format Partition",
            body=f"Select filesystem type for {self.selected_row.partition_path}:\n\nWarning: All data will be lost!",
            transient_for=self.get_root()
        )
        dialog.add_response("cancel", "Cancel")
        for fs in self.FS_CHOICES:
            if fs != "unformatted":
                dialog.add_response(fs, fs.upper())
        dialog.set_response_appearance("ext4", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_format_response)
        dialog.present()

    def _on_format_response(self, dialog, response_id):
        """Handle format response"""
        if response_id in self.FS_CHOICES:
            self._execute_format(response_id)

    def _execute_format(self, filesystem):
        """Execute partition formatting"""
        try:
            progress_dialog = self._show_progress_dialog(
                "Formatting Partition",
                f"Formatting {self.selected_row.partition_path} with {filesystem}..."
            )

            device = self.selected_row.partition_path

            if filesystem == 'ext4':
                cmd = ['sudo', 'mkfs.ext4', '-F', device]
            elif filesystem == 'btrfs':
                cmd = ['sudo', 'mkfs.btrfs', '-f', device]
            elif filesystem == 'xfs':
                cmd = ['sudo', 'mkfs.xfs', '-f', device]
            elif filesystem == 'f2fs':
                cmd = ['sudo', 'mkfs.f2fs', '-f', device]
            elif filesystem == 'vfat':
                cmd = ['sudo', 'mkfs.fat', '-F', '32', device]
            elif filesystem == 'ntfs':
                cmd = ['sudo', 'mkfs.ntfs', '-f', device]
            elif filesystem == 'exfat':
                cmd = ['sudo', 'mkfs.exfat', device]
            elif filesystem == 'swap':
                cmd = ['sudo', 'mkswap', device]
            else:
                raise Exception(f"Unsupported filesystem: {filesystem}")

            process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if process.returncode != 0:
                raise Exception(f"Formatting failed: {process.stderr}")

            # Create Btrfs subvolumes if formatting as root
            if filesystem == 'btrfs' and device in self.partition_config:
                if self.partition_config[device].get('mountpoint') == '/':
                    self._create_btrfs_subvolumes(device)

            progress_dialog.destroy()
            self._show_info_dialog("Success", f"Partition formatted successfully with {filesystem}")
            self._on_refresh(None)

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.destroy()
            self._show_error_dialog("Error", f"Failed to format partition: {str(e)}")

    def _create_btrfs_subvolumes(self, device):
        """Create Btrfs subvolumes"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Mount
                cmd = ['sudo', 'mount', device, tmpdir]
                subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)

                try:
                    # Create subvolumes
                    for subvol in ['@', '@home', '@var', '@tmp', '@snapshots']:
                        cmd = ['sudo', 'btrfs', 'subvolume', 'create', f"{tmpdir}/{subvol}"]
                        subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                    # Set default subvolume to @
                    cmd = ['sudo', 'btrfs', 'subvolume', 'list', tmpdir]
                    process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if process.returncode == 0:
                        for line in process.stdout.split('\n'):
                            if ' path @' in line and line.endswith(' path @'):
                                subvol_id = line.split()[1]
                                cmd = ['sudo', 'btrfs', 'subvolume', 'set-default', subvol_id, tmpdir]
                                subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                                break
                finally:
                    time.sleep(1)
                    cmd = ['sudo', 'umount', tmpdir]
                    subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        except Exception as e:
            print(f"Warning: Failed to create Btrfs subvolumes: {e}")

    def _show_partition_dialog(self, row=None, is_new=False):
        """Show partition creation/edit dialog"""
        dialog = Gtk.Dialog(
            title="Partition Editor" if not is_new else "Create Partition",
            transient_for=self.get_root(),
            modal=True
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        dialog.set_default_size(400, -1)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        # Size input (only for new partitions)
        if is_new:
            size_label = Gtk.Label(label="Size:", xalign=0)
            content.append(size_label)

            size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            entry_size = Gtk.Entry()
            entry_size.set_placeholder_text("10 or leave empty for max")
            entry_size.set_hexpand(True)
            size_box.append(entry_size)

            unit_combo = Gtk.ComboBoxText()
            for u in self.SIZE_UNITS:
                unit_combo.append_text(u)
            unit_combo.set_active(1)  # Default GB
            size_box.append(unit_combo)
            content.append(size_box)
        else:
            entry_size = None
            unit_combo = None

        # Mount point
        mount_label = Gtk.Label(label="Mount Point:", xalign=0)
        content.append(mount_label)

        entry_mount = Gtk.Entry()
        entry_mount.set_placeholder_text("/home, /boot, etc.")
        if row:
            entry_mount.set_text(row.mount_point)
        content.append(entry_mount)

        # Common mount points buttons
        common_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Check boot mode to show appropriate boot mountpoint
        boot_mode = self._detect_boot_mode()
        boot_mp = "/boot/efi" if boot_mode == "uefi" else "/boot"

        for mp in ["/", "/home", boot_mp, "/var", "/tmp"]:
            btn = Gtk.Button(label=mp)
            btn.connect("clicked", lambda b, m=mp: entry_mount.set_text(m))
            common_box.append(btn)
        content.append(common_box)

        # Filesystem
        fs_label = Gtk.Label(label="Filesystem:", xalign=0)
        content.append(fs_label)

        fs_combo = Gtk.ComboBoxText()
        for fs in self.FS_CHOICES:
            fs_combo.append_text(fs)

        if row and row.fstype in self.FS_CHOICES:
            fs_combo.set_active(self.FS_CHOICES.index(row.fstype))
        else:
            fs_combo.set_active(0)  # Default ext4
        content.append(fs_combo)

        # Boot flag checkbox
        boot_check = Gtk.CheckButton(label="Mark as bootable")
        if row:
            boot_check.set_active(row.is_bootable)
        content.append(boot_check)

        def on_response(dlg, resp):
            if resp == Gtk.ResponseType.OK:
                mount = entry_mount.get_text().strip()
                fs = fs_combo.get_active_text()
                is_bootable = boot_check.get_active()

                if is_new:
                    # Create new partition
                    size = entry_size.get_text().strip()
                    unit = unit_combo.get_active_text()
                    size_str = f"{size}{unit}" if size else "100%"
                    self._execute_create_partition(size_str, fs, mount, is_bootable)
                else:
                    # Edit existing partition
                    device = row.partition_path

                    # Update configuration
                    if device not in self.partition_config:
                        self.partition_config[device] = {}

                    self.partition_config[device]['mountpoint'] = mount
                    self.partition_config[device]['bootable'] = is_bootable
                    self.partition_config[device]['fstype'] = fs

                    # Update display
                    row.mount_point = mount
                    row.mount_label.set_text(mount or "(none)")
                    row.fs_label.set_text(fs)
                    row.is_bootable = is_bootable
                    row.icon.set_from_icon_name(
                        "emblem-system-symbolic" if is_bootable else "drive-removable-media-symbolic"
                    )

                    self._save_partition_config()
                    self._generate_and_apply_fstab()
                    self._update_proceed_sensitive()

                    self._show_info_dialog("Success", f"Partition {device} updated")

            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _execute_create_partition(self, size, filesystem, mountpoint, is_bootable):
        """Execute partition creation"""
        try:
            progress_dialog = self._show_progress_dialog(
                "Creating Partition",
                "Creating new partition..."
            )

            disk = self.selected_disk

            # Check if disk has partition table
            cmd = ['sudo', 'parted', disk, 'print']
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if "unrecognised disk label" in process.stderr.lower() or "unrecognized disk label" in process.stderr.lower():
                # Create GPT by default
                cmd = ['sudo', 'parted', '-s', disk, 'mklabel', 'gpt']
                subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
                time.sleep(1)

            # Find free space
            cmd = ['sudo', 'parted', disk, 'unit', 'B', 'print', 'free']
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if process.returncode != 0:
                raise Exception(f"Failed to get disk info: {process.stderr}")

            # Parse free space
            lines = process.stdout.split('\n')
            free_start = None
            free_end = None
            max_size = 0

            for line in lines:
                if 'Free Space' in line:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        try:
                            start = int(parts[0].replace('B', ''))
                            end = int(parts[1].replace('B', ''))
                            size_bytes = end - start
                            if size_bytes > max_size:
                                free_start = start
                                free_end = end
                                max_size = size_bytes
                        except ValueError:
                            continue

            if free_start is None:
                raise Exception("No free space found")

            # Calculate partition size
            sector_size = 512
            free_start = ((free_start // sector_size) + 1) * sector_size

            if size == "100%":
                free_end = (free_end // sector_size) * sector_size
                end_pos = f"{free_end}B"
            else:
                # Convert size to bytes
                size_mb = self._convert_size_to_mb(size)
                if size_mb is None:
                    raise Exception(f"Invalid size format: {size}")

                size_bytes = int(size_mb * 1024 * 1024)
                available = free_end - free_start

                if size_bytes > available:
                    raise Exception(f"Requested size exceeds available space")

                free_end = free_start + size_bytes
                free_end = (free_end // sector_size) * sector_size
                end_pos = f"{free_end}B"

            start_pos = f"{free_start}B"

            # Create partition
            cmd = ['sudo', 'parted', '-s', disk, 'mkpart', 'primary', start_pos, end_pos]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if process.returncode != 0:
                raise Exception(f"Failed to create partition: {process.stderr}")

            # Force kernel to re-read partition table
            cmd = ['sudo', 'partprobe', disk]
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            time.sleep(2)

            # Get new partition path
            cmd = ['sudo', 'parted', disk, 'print']
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            partition_num = 0
            for line in process.stdout.split('\n'):
                line = line.strip()
                if line and line[0].isdigit():
                    parts = line.split()
                    if len(parts) >= 1:
                        try:
                            num = int(parts[0])
                            partition_num = max(partition_num, num)
                        except ValueError:
                            continue

            if partition_num == 0:
                raise Exception("Could not determine partition number")

            new_partition = DiskUtils.get_partition_path(disk, partition_num)

            # Format if filesystem specified
            if filesystem and filesystem != 'unformatted':
                self._format_partition_sync(new_partition, filesystem)

            # Set boot flag if requested
            if is_bootable:
                cmd = ['sudo', 'parted', '-s', disk, 'set', str(partition_num), 'boot', 'on']
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Update configuration
            self.partition_config[new_partition] = {
                'mountpoint': mountpoint,
                'bootable': is_bootable,
                'fstype': filesystem
            }

            self._save_partition_config()
            self._generate_and_apply_fstab()

            progress_dialog.destroy()
            self._show_info_dialog("Success", f"Partition {new_partition} created successfully")
            self._on_refresh(None)

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.destroy()
            self._show_error_dialog("Error", f"Failed to create partition: {str(e)}")

    def _format_partition_sync(self, device, filesystem):
        """Format partition synchronously"""
        if filesystem == 'ext4':
            cmd = ['sudo', 'mkfs.ext4', '-F', device]
        elif filesystem == 'btrfs':
            cmd = ['sudo', 'mkfs.btrfs', '-f', device]
        elif filesystem == 'xfs':
            cmd = ['sudo', 'mkfs.xfs', '-f', device]
        elif filesystem == 'f2fs':
            cmd = ['sudo', 'mkfs.f2fs', '-f', device]
        elif filesystem == 'vfat':
            cmd = ['sudo', 'mkfs.fat', '-F', '32', device]
        elif filesystem == 'ntfs':
            cmd = ['sudo', 'mkfs.ntfs', '-f', device]
        elif filesystem == 'exfat':
            cmd = ['sudo', 'mkfs.exfat', device]
        elif filesystem == 'swap':
            cmd = ['sudo', 'mkswap', device]
        else:
            return

        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)

    def _convert_size_to_mb(self, size_str):
        """Convert size string to MB"""
        try:
            if size_str.upper().endswith('GB'):
                return float(size_str[:-2]) * 1000
            elif size_str.upper().endswith('TB'):
                return float(size_str[:-2]) * 1000000
            elif size_str.upper().endswith('MB'):
                return float(size_str[:-2])
            elif size_str.upper().endswith('KB'):
                return float(size_str[:-2]) / 1000
            else:
                return float(size_str)
        except (ValueError, IndexError):
            return None

    def init_partition_config(self):
        """Initialize partition configuration"""
        self._load_partition_config()

    def _load_partition_config(self):
        """Load partition configuration from file"""
        try:
            config_path = "/tmp/installer_config/.disk_utility_config.json"

            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.partition_config = json.load(f)
            else:
                self.partition_config = {}
        except Exception:
            self.partition_config = {}

    def _save_partition_config(self):
        """Save partition configuration to file"""
        try:
            config_dir = "/tmp/installer_config"
            os.makedirs(config_dir, exist_ok=True)

            config_path = os.path.join(config_dir, ".disk_utility_config.json")

            with open(config_path, 'w') as f:
                json.dump(self.partition_config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _generate_and_apply_fstab(self):
        """Generate fstab file"""
        try:
            fstab_content = [
                "# /etc/fstab: static file system information.",
                "#",
                "# <file system>             <mount point>  <type>  <options>         <dump>  <pass>",
                "# Generated by Pelican Installer",
                ""
            ]

            if not self.partition_config:
                fstab_content.append("# No partition configuration found")
            else:
                btrfs_root_device = None
                btrfs_root_uuid = None

                # Find Btrfs root
                for device, config in self.partition_config.items():
                    if config.get('mountpoint') == '/':
                        filesystem = config.get('fstype', self._get_filesystem_type(device))
                        if filesystem == 'btrfs':
                            btrfs_root_device = device
                            btrfs_root_uuid = self._get_device_uuid(device)
                            break

                # Generate entries
                for device, config in self.partition_config.items():
                    if 'mountpoint' not in config:
                        continue

                    mountpoint = config['mountpoint']
                    bootable = config.get('bootable', False)
                    filesystem = config.get('fstype', self._get_filesystem_type(device) or 'auto')

                    uuid = self._get_device_uuid(device)

                    # Handle Btrfs subvolumes
                    if device == btrfs_root_device and filesystem == 'btrfs':
                        for subvol, mount in self.btrfs_subvolumes.items():
                            device_id = f"UUID={uuid}" if uuid else device
                            options = f"subvol={subvol},defaults,compress=zstd,noatime"
                            dump = "0"
                            pass_num = "1" if mount == "/" else "2"

                            fstab_line = f"{device_id:<25} {mount:<15} {filesystem:<7} {options:<40} {dump:<6} {pass_num}"
                            fstab_content.append(fstab_line)
                    else:
                        if filesystem == "swap":
                            options = "defaults"
                            dump = "0"
                            pass_num = "0"
                        elif mountpoint == "/":
                            options = "defaults"
                            dump = "1"
                            pass_num = "1"
                        elif bootable and mountpoint in ["/boot", "/boot/efi"]:
                            options = "defaults"
                            dump = "1"
                            pass_num = "2"
                        else:
                            options = "defaults"
                            dump = "0"
                            pass_num = "2"

                        device_id = f"UUID={uuid}" if uuid else device
                        fstab_line = f"{device_id:<25} {mountpoint:<15} {filesystem:<7} {options:<15} {dump:<6} {pass_num}"
                        fstab_content.append(fstab_line)

            # Save fstab
            etc_dir = "/tmp/installer_config/etc"
            os.makedirs(etc_dir, exist_ok=True)

            fstab_path = os.path.join(etc_dir, "fstab")
            with open(fstab_path, 'w') as f:
                f.write('\n'.join(fstab_content))

            print(f"Generated fstab saved to: {fstab_path}")

        except Exception as e:
            print(f"Error generating fstab: {e}")

    def _get_filesystem_type(self, device):
        """Get filesystem type of a device"""
        try:
            cmd = ['sudo', 'blkid', '-o', 'value', '-s', 'TYPE', device]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if process.returncode == 0:
                return process.stdout.strip()
        except Exception:
            pass
        return None

    def _get_device_uuid(self, device):
        """Get UUID of a device"""
        try:
            cmd = ['sudo', 'blkid', '-o', 'value', '-s', 'UUID', device]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if process.returncode == 0:
                uuid = process.stdout.strip()
                return uuid if uuid else None
        except Exception:
            pass
        return None

    def _clear_list(self):
        """Clear partition list"""
        while True:
            row = self.listbox.get_row_at_index(0)
            if not row:
                break
            self.listbox.remove(row)

    def _add_error_row(self, text):
        """Add error row to list"""
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=text, xalign=0)
        lbl.get_style_context().add_class("error")
        row.set_child(lbl)
        self.listbox.append(row)

    def _add_info_row(self, text):
        """Add info row to list"""
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=text, xalign=0)
        lbl.add_css_class("dim-label")
        row.set_child(lbl)
        self.listbox.append(row)

    def _update_proceed_sensitive(self):
        """Update proceed button sensitivity"""
        has_root = False
        has_boot = False

        for device, config in self.partition_config.items():
            if config.get('mountpoint') == '/':
                has_root = True
            if config.get('bootable', False):
                has_boot = True

        self.btn_proceed.set_sensitive(has_root and has_boot)

    def _show_error_dialog(self, heading, message):
        """Show error dialog"""
        dialog = Adw.MessageDialog(
            heading=heading,
            body=message,
            transient_for=self.get_root()
        )
        dialog.add_response("ok", "OK")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.present()

    def _show_info_dialog(self, heading, message):
        """Show info dialog"""
        dialog = Adw.MessageDialog(
            heading=heading,
            body=message,
            transient_for=self.get_root()
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def _show_progress_dialog(self, heading, message):
        """Show progress dialog with spinner"""
        dialog = Adw.MessageDialog(
            heading=heading,
            body=message,
            transient_for=self.get_root()
        )

        spinner = Gtk.Spinner()
        spinner.start()
        spinner.set_size_request(32, 32)

        content_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        content_area.set_halign(Gtk.Align.CENTER)
        content_area.append(spinner)
        content_area.append(Gtk.Label(label="Please wait..."))

        dialog.set_extra_child(content_area)
        dialog.present()

        return dialog

    def _on_back(self, button):
        """Handle back button"""
        if hasattr(self.app, "go_to"):
            self.app.go_to("keyboard")

    def _on_proceed(self, button):
        """Handle proceed button with validation"""
        has_root = False
        has_boot = False

        for device, config in self.partition_config.items():
            if config.get('mountpoint') == '/':
                has_root = True
            if config.get('bootable', False):
                has_boot = True

        if not has_root or not has_boot:
            missing = []
            if not has_root:
                missing.append("• Root (/) mountpoint")
            if not has_boot:
                missing.append("• Bootable partition")

            self._show_error_dialog(
                "Missing Configuration",
                f"The following are required:\n\n{chr(10).join(missing)}"
            )
            return

        if hasattr(self.app, "go_to"):
            self.app.go_to("install-summary")
