#!/usr/bin/env python3

import os
import gi
import subprocess
import threading
import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Callable, Optional


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango, GObject
from simple_localization_manager import get_localization_manager

class InstallationState(Enum):
    """Enumeration of installation states."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"

@dataclass
class InstallationStep:
    """Data class representing a single installation step."""
    label: str
    command: List[str]
    description: str = ""
    weight: float = 1.0  # Weight for progress calculation
    critical: bool = True  # If True, failure stops installation
    
class InstallationWidget(Gtk.Box):
    """
    A GTK widget for displaying installation progress with detailed logging.
    Executes shell commands sequentially with progress tracking.
    """
    
    __gsignals__ = {
        'installation-complete': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'installation-error': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'installation-cancelled': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(20)
        self.set_margin_top(30)
        self.set_margin_bottom(30)

        
        # State tracking
        self.state = InstallationState.IDLE
        self.current_step = 0
        self.installation_steps: List[InstallationStep] = []
        self.installation_thread = None
        self.should_cancel = False
        self.show_details = False
        self.log_buffer = []
        self.start_time = None
        
        # Callbacks
        self.on_complete_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        # Build UI
        self._build_ui()

    
    def _build_ui(self):
        """Build the user interface."""
        
        # --- Title Section ---
        self.title = Gtk.Label()
        localization_manager = get_localization_manager()
        self.title.set_markup(f'<span size="xx-large" weight="bold">{localization_manager.get_text("Installing System")}</span>')
        self.title.set_halign(Gtk.Align.CENTER)
        self.append(self.title)
        
        # --- Main Content Clamp ---
        clamp = Adw.Clamp(margin_start=12, margin_end=12, maximum_size=700)
        clamp.set_vexpand(True)
        self.append(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content_box)
        
        # --- Status Section ---
        status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        status_card.add_css_class('card')
        status_card.set_margin_top(10)
        status_card.set_margin_bottom(10)
        status_card.set_margin_start(10)
        status_card.set_margin_end(10)
        content_box.append(status_card)
        
        # Current operation label
        self.operation_label = Gtk.Label(label="Preparing installation...")
        self.operation_label.set_halign(Gtk.Align.START)
        self.operation_label.set_markup('<b>Preparing installation...</b>')
        self.operation_label.set_margin_top(10)
        self.operation_label.set_margin_bottom(10)
        self.operation_label.set_margin_start(10)
        self.operation_label.set_margin_end(10)
        status_card.append(self.operation_label)
        
        # Current step description
        self.step_description = Gtk.Label(label="Please wait while the system prepares for installation")
        self.step_description.set_halign(Gtk.Align.START)
        self.step_description.set_wrap(True)
        self.step_description.add_css_class('dim-label')
        self.step_description.set_margin_top(10)
        self.step_description.set_margin_bottom(10)
        self.step_description.set_margin_start(10)
        self.step_description.set_margin_end(10)
        status_card.append(self.step_description)
        
        # --- Progress Section ---
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content_box.append(progress_box)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("0%")
        progress_box.append(self.progress_bar)
        
        # Step counter
        self.step_counter = Gtk.Label(label="Step 0 of 0")
        self.step_counter.add_css_class('dim-label')
        self.step_counter.set_halign(Gtk.Align.CENTER)
        progress_box.append(self.step_counter)
        
        # Time elapsed
        self.time_label = Gtk.Label(label="Elapsed time: 00:00")
        self.time_label.add_css_class('dim-label')
        self.time_label.set_halign(Gtk.Align.CENTER)
        progress_box.append(self.time_label)
        
        # --- Details Section ---
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.append(details_box)
        
        # Toggle details button
        self.toggle_details_btn = Gtk.Button(label="Show Details")
        self.toggle_details_btn.set_halign(Gtk.Align.CENTER)
        self.toggle_details_btn.connect("clicked", self._on_toggle_details)
        details_box.append(self.toggle_details_btn)
        
        # Details revealer
        self.details_revealer = Gtk.Revealer()
        self.details_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.details_revealer.set_transition_duration(200)
        details_box.append(self.details_revealer)
        
        # Terminal output view
        terminal_frame = Gtk.Frame()
        terminal_frame.set_margin_top(10)
        self.details_revealer.set_child(terminal_frame)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_min_content_height(200)
        scrolled_window.set_max_content_height(400)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        terminal_frame.set_child(scrolled_window)
        
        self.terminal_view = Gtk.TextView()
        self.terminal_view.set_editable(False)
        self.terminal_view.set_monospace(True)
        self.terminal_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.terminal_view.set_margin_top(5)
        self.terminal_view.set_margin_bottom(5)
        self.terminal_view.set_margin_start(5)
        self.terminal_view.set_margin_end(5)
        
        # Set terminal-like styling
        self.terminal_buffer = self.terminal_view.get_buffer()
        self.terminal_view.add_css_class('terminal')
        
        # Create tags for different output types
        self.terminal_buffer.create_tag("command", weight=Pango.Weight.BOLD, foreground="lightblue")
        self.terminal_buffer.create_tag("success", foreground="lightgreen")
        self.terminal_buffer.create_tag("error", foreground="red")
        self.terminal_buffer.create_tag("info", foreground="yellow")
        
        scrolled_window.set_child(self.terminal_view)
        
        # --- Action Buttons ---
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        self.append(button_box)
        
        self.btn_cancel = Gtk.Button(label="Cancel")
        self.btn_cancel.add_css_class('destructive-action')
        self.btn_cancel.add_css_class('buttons_all')
        self.btn_cancel.connect("clicked", self._on_cancel_clicked)
        button_box.append(self.btn_cancel)
        
        self.btn_continue = Gtk.Button(label="Continue")
        self.btn_continue.add_css_class('suggested-action')
        self.btn_continue.add_css_class('buttons_all')
        self.btn_continue.set_sensitive(False)
        self.btn_continue.set_visible(False)
        self.btn_continue.connect("clicked", self._on_continue_clicked)
        button_box.append(self.btn_continue)
        
        # Start timer update
        GLib.timeout_add(1000, self._update_timer)

    
    def _get_mount_root_command(self):
        """Generate a bash command to parse fstab and mount root device."""
        return """
        FSTAB_FILE="/etc/fstab"
        if [ ! -f "$FSTAB_FILE" ]; then
            echo "Error: /etc/fstab not found"
            exit 1
        fi
        
        # Parse fstab for root device (looking for mount point "/")
        ROOT_DEVICE=$(awk '$2 == "/" && $1 !~ /^#/ {print $1}' "$FSTAB_FILE" | head -n1)
        
        if [ -z "$ROOT_DEVICE" ]; then
            echo "Error: Could not find root device in /etc/fstab"
            exit 1
        fi
        
        # Handle UUID and LABEL
        if [[ "$ROOT_DEVICE" == UUID=* ]]; then
            UUID="${ROOT_DEVICE#UUID=}"
            ROOT_DEVICE="/dev/disk/by-uuid/$UUID"
        elif [[ "$ROOT_DEVICE" == LABEL=* ]]; then
            LABEL="${ROOT_DEVICE#LABEL=}"
            ROOT_DEVICE="/dev/disk/by-label/$LABEL"
        fi
        
        echo "Mounting root device: $ROOT_DEVICE"
        mount "$ROOT_DEVICE" "/tmp/linexin_installer/root"
        """
    
    def _get_mount_boot_command(self):
        """Generate a bash command to parse fstab and mount boot device."""
        return """
        FSTAB_FILE="/etc/fstab"
        if [ ! -f "$FSTAB_FILE" ]; then
            echo "Warning: /etc/fstab not found, skipping boot partition"
            exit 0
        fi
        
        # Parse fstab for boot device (looking for mount point "/boot")
        BOOT_DEVICE=$(awk '$2 == "/boot" && $1 !~ /^#/ {print $1}' "$FSTAB_FILE" | head -n1)
        
        if [ -z "$BOOT_DEVICE" ]; then
            echo "No separate /boot partition found in /etc/fstab (boot might be on root partition)"
            exit 0
        fi
        
        # Handle UUID and LABEL
        if [[ "$BOOT_DEVICE" == UUID=* ]]; then
            UUID="${BOOT_DEVICE#UUID=}"
            BOOT_DEVICE="/dev/disk/by-uuid/$UUID"
        elif [[ "$BOOT_DEVICE" == LABEL=* ]]; then
            LABEL="${BOOT_DEVICE#LABEL=}"
            BOOT_DEVICE="/dev/disk/by-label/$LABEL"
        fi
        
        echo "Mounting boot device: $BOOT_DEVICE"
        mount "$BOOT_DEVICE" "/tmp/linexin_installer/root/boot"
        """
    
    def _get_copy_config_command(self):
        """Generate a bash command to copy installer configuration files."""
        return """
        CONFIG_DIR="/tmp/installer_config"
        TARGET_DIR="/tmp/linexin_installer/root"
        
        if [ ! -d "$CONFIG_DIR" ]; then
            echo "No installer configuration directory found at $CONFIG_DIR, skipping"
            exit 0
        fi
        
        echo "Copying configuration files from $CONFIG_DIR to $TARGET_DIR"
        
        # Use rsync to copy and replace files, preserving permissions
        rsync -av --no-owner --no-group "$CONFIG_DIR/" "$TARGET_DIR/"
        
        echo "Configuration files copied successfully"
        """
    
    def start_installation(self, loop_device="/dev/loop0"):
        """Start the installation process.
        
        Args:
            loop_device: The loop device containing the rootfs image
        """
        if self.state == InstallationState.RUNNING:
            return
        
        # Setup installation steps
        steps = []
        
        # All commands will be run with sudo since we're on live-cd with passwordless sudo
        steps.append(InstallationStep(
            label="Creating installation directories",
            command=["sudo", "mkdir", "-p", "/tmp/linexin_installer/rootfs", "/tmp/linexin_installer/root"],
            description="Setting up temporary installation directories",
            weight=0.5,
            critical=True
        ))
        
        steps.append(InstallationStep(
            label="Mounting installation image",
            command=["sudo", "mount", loop_device, "/tmp/linexin_installer/rootfs"],
            description=f"Mounting {loop_device} containing the system image",
            weight=1.0,
            critical=True
        ))
        
        steps.append(InstallationStep(
            label="Mounting root partition",
            command=["sudo", "bash", "-c", self._get_mount_root_command()],
            description="Mounting the root partition based on /etc/fstab",
            weight=1.0,
            critical=True
        ))
        
        steps.append(InstallationStep(
            label="Creating boot directory",
            command=["sudo", "mkdir", "-p", "/tmp/linexin_installer/root/boot"],
            description="Creating boot mount point",
            weight=0.2,
            critical=False
        ))
        
        steps.append(InstallationStep(
            label="Mounting boot partition",
            command=["sudo", "bash", "-c", self._get_mount_boot_command()],
            description="Mounting the boot partition based on /etc/fstab",
            weight=1.0,
            critical=False
        ))
        
        steps.append(InstallationStep(
            label="Copying system files",
            command=["sudo", "rsync", "-aAXv", "--info=progress2", "/tmp/linexin_installer/rootfs/", "/tmp/linexin_installer/root/"],
            description="Copying the system image to your disk. This may take several minutes...",
            weight=10.0,
            critical=True
        ))
        
        steps.append(InstallationStep(
            label="Verifying file copy",
            command=["sudo", "bash", "-c", "echo 'Files copied:' && find /tmp/linexin_installer/root -type f | wc -l"],
            description="Verifying that files were copied successfully",
            weight=0.5,
            critical=True
        ))
        
        steps.append(InstallationStep(
            label="Removing live ISO fstab",
            command=["sudo", "rm", "-f", "/etc/fstab"],
            description="Removing the live ISO filesystem configuration",
            weight=0.1,
            critical=False
        ))
        
        steps.append(InstallationStep(
            label="Applying installer configuration",
            command=["sudo", "bash", "-c", self._get_copy_config_command()],
            description="Copying installer configuration files to the new system",
            weight=1.0,
            critical=False
        ))
        
        # Post-installation cleanup and configuration steps


        steps.append(InstallationStep(
            label="Copying kernel",
            command=["bash", "-c", "sudo cp -rf /run/archiso/bootmnt/arch/boot/x86_64/* /tmp/linexin_installer/root/boot"],
            description="Ensuring kernel image is present on new rootfs in case of no internet",
            weight=1.0,
            critical=True
        ))

        steps.append(InstallationStep(
            label="Removing wheel sudo configuration",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "rm", "/etc/sudoers.d/g_wheel"],
            description="Removing temporary sudo configuration",
            weight=0.1,
            critical=False
        ))
        
        steps.append(InstallationStep(
            label="Changing system's language",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/language.sh"],
            description="Changing system's language to a selected one",
            weight=1.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Setting up timezone",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/setup_timezone.sh"],
            description="Linking timezone to the selected one in the installer",
            weight=1.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Setting up keyboard layout",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/setup_keyboard.sh"],
            description="Using proper commands in chroot environment to set up keyboard layout",
            weight=1.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Adding user",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/add_users.sh"],
            description="Adding user, setting it's password and hostname for the PC",
            weight=1.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Removing unused microcode",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/remove_ucode.sh"],
            description="Removing ucode for non-used x86_64 processor",
            weight=1.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Cleaning out rootfs",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/post-install.sh"],
            description="Cleaning out rootfs from LiveISO's config and applying post-install scripts",
            weight=5.0,
            critical=True
        ))

        steps.append(InstallationStep(
            label="Installing bootloader",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/bootloader.sh"],
            description="Checking for other systems installed and installing proper bootloader",
            weight=3.0,
            critical=False
        ))
        
        steps.append(InstallationStep(
            label="Removing unused GPU drivers",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/remove_gpu.sh"],
            description="Checking for other systems installed and installing proper bootloader",
            weight=3.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Removing unused microcode",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "/remove_ucode.sh"],
            description="Checking for other systems installed and installing proper bootloader",
            weight=3.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Setting up Flatpak",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "flatpak", "update", "--appstream"],
            description="Installing Flatpak apps and support for AppImage",
            weight=5.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Installing Flatpak and AppImage support",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "flatpak", "install", "app.zen_browser.zen", "io.github.Faugus.faugus-launcher", "it.mijorus.gearlever", "com.github.tchx84.Flatseal", "com.usebottles.bottles", "app.twintaillauncher.ttl", "com.heroicgameslauncher.hgl", "--assumeyes"],
            description="Installing Flatpak apps and support for AppImage",
            weight=5.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Cleaning out rootfs",
            command=["sudo", "arch-chroot", "/tmp/linexin_installer/root", "bash", "-c", "rm /*.sh"],
            description="Cleaning out rootfs from LiveISO's config and applying post-install scripts",
            weight=1.0,
            critical=False
        ))

        steps.append(InstallationStep(
            label="Unmounting filesystems",
            command=["sudo", "bash", "-c", "umount -R /tmp/linexin_installer/root/boot && umount /tmp/linexin_installer/root && umount /tmp/linexin_installer/rootfs"],
            description="Safely unmounting all filesystems",
            weight=0.5,
            critical=False
        ))
        
        self.installation_steps = steps
        
        self.state = InstallationState.RUNNING
        self.current_step = 0
        self.should_cancel = False
        self.start_time = time.time()
        self.log_buffer.clear()
        
        # Clear terminal
        self.terminal_buffer.set_text("")
        
        # Update UI
        self.btn_cancel.set_sensitive(True)
        self.btn_continue.set_visible(False)
        localization_manager = get_localization_manager()
        self.title.set_markup(f'<span size="xx-large" weight="bold">{localization_manager.get_text("Installing System")}</span>')

        
        # Start installation thread
        self.installation_thread = threading.Thread(target=self._run_installation)
        self.installation_thread.daemon = True
        self.installation_thread.start()
    
    def _run_installation(self):
        """Run the installation process in a separate thread."""
        total_weight = sum(step.weight for step in self.installation_steps)
        completed_weight = 0.0
        
        for i, step in enumerate(self.installation_steps):
            if self.should_cancel:
                GLib.idle_add(self._on_installation_cancelled)
                return
            
            self.current_step = i
            
            # Update UI
            GLib.idle_add(self._update_step_info, step, i)
            
            # Log command execution
            GLib.idle_add(self._append_to_terminal, f"$ {' '.join(step.command)}", "command")
            
            try:
                # Execute command
                process = subprocess.Popen(
                    step.command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Read output in real-time
                while True:
                    if self.should_cancel:
                        process.terminate()
                        GLib.idle_add(self._on_installation_cancelled)
                        return
                    
                    output = process.stdout.readline()
                    if output:
                        GLib.idle_add(self._append_to_terminal, output.rstrip(), None)
                    
                    # Check if process has finished
                    if process.poll() is not None:
                        break
                
                # Get any remaining output
                stdout, stderr = process.communicate()
                if stdout:
                    GLib.idle_add(self._append_to_terminal, stdout.rstrip(), None)
                if stderr:
                    GLib.idle_add(self._append_to_terminal, stderr.rstrip(), "error")
                
                # Check return code
                if process.returncode != 0:
                    if step.critical:
                        error_msg = f"Step failed: {step.label} (exit code: {process.returncode})"
                        GLib.idle_add(self._append_to_terminal, error_msg, "error")
                        GLib.idle_add(self._on_installation_error, error_msg)
                        return
                    else:
                        warning_msg = f"Warning: Non-critical step failed: {step.label}"
                        GLib.idle_add(self._append_to_terminal, warning_msg, "info")
                else:
                    GLib.idle_add(self._append_to_terminal, f"✓ {step.label} completed successfully", "success")
                
            except Exception as e:
                error_msg = f"Error executing step '{step.label}': {str(e)}"
                GLib.idle_add(self._append_to_terminal, error_msg, "error")
                if step.critical:
                    GLib.idle_add(self._on_installation_error, error_msg)
                    return
            
            # Update progress
            completed_weight += step.weight
            progress = completed_weight / total_weight
            GLib.idle_add(self._update_progress, progress)
            
            # Small delay between steps for visibility
            time.sleep(0.5)
        
        # Installation complete
        GLib.idle_add(self._on_installation_complete)
    
    def _update_step_info(self, step: InstallationStep, index: int):
        """Update the UI with current step information."""
        localization_manager = get_localization_manager()
        self.operation_label.set_markup(f'<b>{localization_manager.get_text(step.label)}</b>')
        self.step_description.set_text(localization_manager.get_text(step.description))
        self.step_counter.set_text(f"{localization_manager.get_text('Step')} {index + 1} {localization_manager.get_text('of')} {len(self.installation_steps)}")
        return False
    
    def _update_progress(self, progress: float):
        """Update the progress bar."""
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{int(progress * 100)}%")
        return False
    
    def _append_to_terminal(self, text: str, tag: Optional[str]):
        """Append text to the terminal view."""
        end_iter = self.terminal_buffer.get_end_iter()
        
        if tag:
            self.terminal_buffer.insert_with_tags_by_name(end_iter, text + "\n", tag)
        else:
            self.terminal_buffer.insert(end_iter, text + "\n")
        
        # Auto-scroll to bottom
        self.terminal_view.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)
        
        # Also add to log buffer
        self.log_buffer.append(text)
        
        return False
    
    def _update_timer(self):
        """Update the elapsed time display."""
        if self.state == InstallationState.RUNNING and self.start_time:
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            localization_manager = get_localization_manager()
            self.time_label.set_text(f"{localization_manager.get_text('Elapsed time')}: {minutes:02d}:{seconds:02d}")
        
        return True  # Continue timer
    
    def _on_toggle_details(self, button):
        """Toggle the details view."""
        localization_manager = get_localization_manager()
        self.show_details = not self.show_details
        self.details_revealer.set_reveal_child(self.show_details)
        self.toggle_details_btn.set_label(
            localization_manager.get_text("Hide Details") if self.show_details 
            else localization_manager.get_text("Show Details")
        )
    
    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        if self.state != InstallationState.RUNNING:
            return
        
        # Show confirmation dialog
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Cancel Installation?",
            body="Are you sure you want to cancel the installation? This may leave your system in an incomplete state."
        )
        dialog.add_response("cancel", "Keep Installing")
        dialog.add_response("stop", "Cancel Installation")
        dialog.set_response_appearance("stop", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_cancel_confirmed)
        dialog.present()
    
    def _on_cancel_confirmed(self, dialog, response):
        """Handle cancel confirmation."""
        if response == "stop":
            self.should_cancel = True
            self.btn_cancel.set_sensitive(False)
            localization_manager = get_localization_manager()
            self.operation_label.set_markup(f'<b>{localization_manager.get_text("Cancelling installation...")}</b>')
    
    def _on_continue_clicked(self, button):
        """Handle continue button click."""
        if self.on_complete_callback:
            self.on_complete_callback()
    
    def _on_installation_complete(self):
        """Handle successful installation completion."""
        self.state = InstallationState.SUCCESS
        self.title.set_markup('<span size="xx-large" weight="bold">Installation Complete!</span>')
        self.operation_label.set_markup('<b>System installed successfully</b>')
        self.step_description.set_text("Your system has been installed and is ready to use.")
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("100%")
        
        # Update buttons
        self.btn_cancel.set_visible(False)
        self.btn_continue.set_visible(True)
        self.btn_continue.set_sensitive(True)
        self.btn_continue.set_label("Finish")
        
        # Add success message to terminal
        self._append_to_terminal("\n" + "="*50, "success")
        self._append_to_terminal("INSTALLATION COMPLETED SUCCESSFULLY!", "success")
        self._append_to_terminal("="*50, "success")
        
        # Emit the signal
        self.emit('installation-complete')
        
        if self.on_complete_callback:
            self.on_complete_callback()
        
        return False


        
        # Update buttons
        self.btn_cancel.set_visible(False)
        self.btn_continue.set_visible(True)
        self.btn_continue.set_sensitive(True)
        self.btn_continue.set_label("Finish")
        
        # Add success message to terminal
        self._append_to_terminal("\n" + "="*50, "success")
        self._append_to_terminal("INSTALLATION COMPLETED SUCCESSFULLY!", "success")
        self._append_to_terminal("="*50, "success")
        
        if self.on_complete_callback:
            self.on_complete_callback()
        
        return False
    
    def _on_installation_error(self, error_msg: str):
        """Handle installation error."""
        self.state = InstallationState.ERROR
        localization_manager = get_localization_manager()
        self.title.set_markup(f'<span size="xx-large" weight="bold">{localization_manager.get_text("Installation Failed")}</span>')
        self.operation_label.set_markup(f'<b>{localization_manager.get_text("An error occurred during installation")}</b>')
        self.step_description.set_text(error_msg)
        
        # Update buttons
        self.btn_cancel.set_visible(False)
        self.btn_continue.set_visible(False)
        self.btn_continue.set_sensitive(False)
        self.btn_continue.set_label(localization_manager.get_text("Try Again"))
        
        # Show error dialog
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=localization_manager.get_text("Installation Failed"),
            body=f"{localization_manager.get_text('The installation could not be completed.')}\n\n{localization_manager.get_text('Error')}: {error_msg}\n\n{localization_manager.get_text('Please check the details for more information.')}"
        )
        dialog.add_response("ok", localization_manager.get_text("OK"))
        dialog.present()
        
        if self.on_error_callback:
            self.on_error_callback(error_msg)
        
        return False
    
    def _on_installation_cancelled(self):
        """Handle installation cancellation."""
        self.state = InstallationState.CANCELLED
        localization_manager = get_localization_manager()
        self.title.set_markup(f'<span size="xx-large" weight="bold">{localization_manager.get_text("Installation Cancelled")}</span>')
        self.operation_label.set_markup(f'<b>{localization_manager.get_text("Installation was cancelled by user")}</b>')
        self.step_description.set_text(localization_manager.get_text("The installation process was interrupted."))
        
        # Update buttons
        self.btn_cancel.set_visible(False)
        self.btn_continue.set_visible(False)
        self.btn_continue.set_sensitive(False)
        self.btn_continue.set_label(localization_manager.get_text("Restart"))
        
        self._append_to_terminal(f"\n{localization_manager.get_text('Installation cancelled by user.')}", "info")
        
        return False
    
    def get_installation_log(self) -> List[str]:
        """Get the complete installation log."""
        return self.log_buffer.copy()
    
    def save_log_to_file(self, filepath: str):
        """Save the installation log to a file."""
        try:
            with open(filepath, 'w') as f:
                f.write('\n'.join(self.log_buffer))
            return True
        except Exception as e:
            print(f"Error saving log: {e}")
            return False