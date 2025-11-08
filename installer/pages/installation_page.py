# Main Install Function
import gi
import os
import json
import time
import re
import threading
import subprocess

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
from ..pages.disk_managent import DiskManagent

class InstallationPage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.set_child(self._build_ui())
        self.install_thread = None
        # Lista zadań instalacyjnych
        self.tasks = [
            ("Mounting partitions...", self._mount_partitons),
            ("Initializing OSTree Filesystem...", self._init_ostree_fs),
            ("Deploying OSTree system...", self._deploy_ostree_system),
            ("Installing Bootloader...", self._install_bootloader),
            ("Configuring system...", self._configure_system)
        ]

        # Uruchom instalację automatycznie po załadowaniu UI
        #GLib.idle_add(self.start_installation)

    def _build_ui(self):
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=20,
            margin_top=40,
            margin_bottom=40,
            margin_start=60,
            margin_end=60,
        )
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)

        # Title
        title = Gtk.Label()
        title.set_markup("<big><b>Installing the System</b></big>")
        title.set_halign(Gtk.Align.CENTER)
        main_box.append(title)

        # Status label
        self.status_label = Gtk.Label(label="Preparing installation environment...")
        self.status_label.set_halign(Gtk.Align.CENTER)
        main_box.append(self.status_label)

        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_hexpand(True)
        self.progress.set_vexpand(False)
        main_box.append(self.progress)

        # Button for showing details
        self.toggle_btn = Gtk.Button(label="Show details")
        self.toggle_btn.set_halign(Gtk.Align.CENTER)
        self.toggle_btn.connect("clicked", self._toggle_details)
        main_box.append(self.toggle_btn)

        # Log output area
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_buffer = self.log_view.get_buffer()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.log_view)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_visible(False)
        main_box.append(scrolled)
        self.scrolled = scrolled

        # Bottom button
        self.btn_reboot = Gtk.Button(label="Reboot")
        self.btn_reboot.set_sensitive(False)
        self.btn_reboot.set_halign(Gtk.Align.CENTER)
        self.btn_reboot.connect("clicked", self._on_reboot)
        main_box.append(self.btn_reboot)

        return main_box

    # Installation

    def _toggle_details(self, button):
        if self.scrolled.is_visible():
            self.scrolled.set_visible(False)
            button.set_label("Show details")
        else:
            self.scrolled.set_visible(True)
            button.set_label("Hide details")

    def _on_reboot(self, button):
        self._append_log("Rebooting system...\n")
        try:
            # Można spróbować zrestartować system (jeśli ma uprawnienia)
            subprocess.run(["systemctl", "reboot"], check=False)
        except Exception as e:
            self._append_log(f"[ERROR] Failed to reboot: {e}\n")



    def start_installation(self):
        if self.install_thread and self.install_thread.is_alive():
            return  # already running

        self.install_thread = threading.Thread(target=self._run_installation_tasks)
        self.install_thread.start()

    def _run_installation_tasks(self):
        total = len(self.tasks)

        for i, (desc, func) in enumerate(self.tasks, start=1):
            GLib.idle_add(self._update_status, desc, i - 1, total)
            try:
                func()
            except Exception as e:
                GLib.idle_add(self._append_log, f"[ERROR] {desc}: {e}\n")
                continue

        GLib.idle_add(self._installation_complete)

    def _update_status(self, text, step, total):
        self.status_label.set_text(text)
        self.progress.set_fraction(step / total)
        return False

    def _append_log(self, message):
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, message)
        return False

    def _installation_complete(self):
        self.status_label.set_text("Installation completed successfully!")
        self.progress.set_fraction(1.0)
        self.btn_reboot.set_sensitive(True)
        return False

    # Mounting Partitons

    def _mount_partitons(self):
        config = self.app.managent_part_page._load_partition_config_with_return()
        target_root = "/mnt/pelican_root"
        os.makedirs(target_root, exist_ok=True)
        self._append_log("Starting partition mounting...\n")

        total_parts = len(config)
        done = 0

        # Najpierw root
        for device, info in config.items():
            if info.get("mountpoint") == "/":
                try:
                    subprocess.run(["mount", "-t", info.get("fstype", "auto"), device, target_root], check=True)
                    self._append_log(f"Mounted root ({device}) to {target_root}\n")
                except subprocess.CalledProcessError as e:
                    self._append_log(f"[ERROR] Failed to mount root: {e}\n")
                    return False
                done += 1
                GLib.idle_add(self.progress.set_fraction, done / total_parts)
                break

        # Potem reszta
        for device, info in config.items():
            mp = info.get("mountpoint")
            if mp in [None, "", "/"]:
                continue

            full_mount_path = os.path.join(target_root, mp.lstrip("/"))
            os.makedirs(full_mount_path, exist_ok=True)
            fstype = info.get("fstype", "auto")

            try:
                subprocess.run(["mount", "-t", fstype, device, full_mount_path], check=True)
                self._append_log(f"Mounted {device} -> {full_mount_path}\n")
            except subprocess.CalledProcessError as e:
                self._append_log(f"[ERROR] Failed to mount {device}: {e}\n")

            done += 1
            GLib.idle_add(self.progress.set_fraction, done / total_parts)

        self._append_log("All partitions mounted successfully.\n")
        return True

    # Initliazing OSTree Filesystem
    def _init_ostree_fs(self):
        self._append_log("Initializing OSTree filesystem...\n")

        target_root = "/mnt/pelican_root"

        try:
            os.makedirs(target_root, exist_ok=True)

            subprocess.run(
                ["ostree", "admin", "init-fs", target_root],
                check=True
                )
            self._append_log("OSTree filesystem initialized successfully.\n")

        except subprocess.CalledProcessError as e:
            self._append_log(f"[ERROR] Failed to initialize OSTree filesystem: {e}\n")
            raise e
        except Exception as e:
            self._append_log(f"[ERROR] Unexcepted error: {e}\n")
            raise e

        return True

    # Deploy OSTree System
    def _deploy_ostree_system(self):
        self._append_log("Deploying OSTree system with pacman-ostree...\n")

        target_root = "/mnt/pelican_root"
        stateroot = "pelican"
        registry_conf = "/etc/pelican-installer/registry.conf"

        try:
            # Wczytanie nazwy obrazu
            if not os.path.exists(registry_conf):
                raise FileNotFoundError(f"Registry config not found: {registry_conf}")

            with open(registry_conf, "r") as f:
                image_ref = f.readline().strip()

            if not image_ref:
                raise ValueError("Image reference in registry.conf is empty")

            self._append_log(f"Loaded image reference: {image_ref}\n")

            # Budujemy komendę pacman-ostree
            cmd = [
                "pacman-ostree",
                "ostree", "container", "image", "deploy",
                "--sysroot", target_root,
                "--stateroot", stateroot,
                "--image", image_ref,
                "--transport", "registry",
                "--insecure-skip-tls-verification"
            ]

            self._append_log(f"Running: {' '.join(cmd)}\n")

            # Uruchamiamy proces z przekierowaniem logów
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                GLib.idle_add(self._append_log, line)

            process.wait()

            if process.returncode != 0:
                self._append_log("[ERROR] pacman-ostree deployment failed!\n")
                raise subprocess.CalledProcessError(process.returncode, cmd)

            self._append_log("OSTree system deployed successfully.\n")

        except FileNotFoundError as e:
            self._append_log(f"[ERROR] {e}\n")
            raise e
        except subprocess.CalledProcessError as e:
            self._append_log(f"[ERROR] Failed to deploy system: {e}\n")
            raise e
        except Exception as e:
            self._append_log(f"[ERROR] Unexpected error: {e}\n")
            raise e

        return True

    def _install_bootloader(self):
        self._append_log("Installing Bootloader...\n")
        target_root = "/mnt/pelican_root"

        # Wczytaj konfigurację partycji
        config = self.app.managent_part_page._load_partition_config_with_return()
        os.makedirs(target_root, exist_ok=True)

        boot_device = None

        # Znajdź urządzenie z mountpointem /boot lub /boot/efi
        for device, info in config.items():
            mp = info.get("mountpoint", "")
            if mp in ("/boot", "/boot/efi"):
                boot_device = device
                break

        if not boot_device:
            self._append_log("[ERROR] No /boot or /boot/efi partition found in configuration!\n")
            return False

        # Usuń numer partycji — działa dla /dev/sda2, /dev/vda1, /dev/nvme0n1p3
        base_device = re.sub(r"p?\d+$", "", boot_device)
        self._append_log(f"Detected boot device: {boot_device} -> base: {base_device}\n")

        try:
            # Zbuduj komendę — uwaga: DEST_ROOT jest argumentem pozycyjnym!
            cmd = [
                "bootupctl", "backend", "install",
                "--auto",
                "--write-uuid",
                "--update-firmware",
                "--device", base_device,
                target_root
            ]

            self._append_log(f"Running: {' '.join(cmd)}\n")

            # Uruchom proces i przekieruj logi do GUI
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                GLib.idle_add(self._append_log, line)

            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)

            self._append_log("Bootloader installed successfully.\n")

        except subprocess.CalledProcessError as e:
            self._append_log(f"[ERROR] Bootloader installation failed: {e}\n")
            raise e
        except Exception as e:
            self._append_log(f"[ERROR] Unexpected error during bootloader installation: {e}\n")
            raise e

        return True

    def _configure_system(self):
        self._append_log(f"Not implemented yet.")
        return True








