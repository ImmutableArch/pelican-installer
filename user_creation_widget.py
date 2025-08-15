#!/usr/bin/env python3

import os
import gi
import json
import hashlib
import random
import string
import re
import subprocess

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

class UserCreationWidget(Gtk.Box):
    """
    A GTK widget for creating user accounts during system installation.
    Handles user creation, root account setup, and generates configuration files.
    """
    def __init__(self, config_output_dir=None, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(20)
        self.set_margin_top(30)
        self.set_margin_bottom(30)
        
        # State tracking
        self.root_enabled = False
        self.validation_errors = set()
        
        # Configuration output directory
        # Default to /tmp which is usually tmpfs but has more space allocated
        # Or use a custom directory (like a mounted partition)
        self.config_output_dir = config_output_dir or "/tmp"
        
        # --- Title Label ---
        self.title = Gtk.Label()
        self.title.set_markup('<span size="xx-large" weight="bold">Create Your User Account</span>')
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
            label="Set up your account to log in to the system.",
            halign=Gtk.Align.CENTER
        )
        self.subtitle.add_css_class('dim-label')
        content_box.append(self.subtitle)
        
        # --- Scrolled Window for the form ---
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        content_box.append(scrolled_window)
        
        # Form container
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        form_box.set_margin_top(20)
        form_box.set_margin_start(20)
        form_box.set_margin_end(20)
        scrolled_window.set_child(form_box)
        
        # --- User Account Section ---
        user_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        form_box.append(user_section)
        
        user_header = Gtk.Label(label="User Account", xalign=0)
        user_header.set_markup('<b>User Account</b>')
        user_section.append(user_header)
        
        # Username field
        username_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        user_section.append(username_box)
        
        username_label = Gtk.Label(label="Username", xalign=0)
        username_label.add_css_class('dim-label')
        username_box.append(username_label)
        
        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("e.g., john")
        self.username_entry.connect("changed", self.validate_fields)
        username_box.append(self.username_entry)
        
        self.username_error = Gtk.Label(xalign=0)
        self.username_error.add_css_class('error')
        self.username_error.set_visible(False)
        username_box.append(self.username_error)
        
        # Full Name field
        fullname_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        user_section.append(fullname_box)
        
        fullname_label = Gtk.Label(label="Full Name", xalign=0)
        fullname_label.add_css_class('dim-label')
        fullname_box.append(fullname_label)
        
        self.fullname_entry = Gtk.Entry()
        self.fullname_entry.set_placeholder_text("e.g., John Doe")
        self.fullname_entry.connect("changed", self.validate_fields)
        fullname_box.append(self.fullname_entry)
        
        # Password field
        password_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        user_section.append(password_box)
        
        password_label = Gtk.Label(label="Password", xalign=0)
        password_label.add_css_class('dim-label')
        password_box.append(password_label)
        
        self.password_entry = Gtk.PasswordEntry()
        self.password_entry.set_show_peek_icon(True)
        self.password_entry.connect("changed", self.validate_fields)
        password_box.append(self.password_entry)
        
        self.password_strength = Gtk.Label(xalign=0)
        self.password_strength.add_css_class('dim-label')
        password_box.append(self.password_strength)
        
        # Repeat Password field
        repeat_password_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        user_section.append(repeat_password_box)
        
        repeat_password_label = Gtk.Label(label="Repeat Password", xalign=0)
        repeat_password_label.add_css_class('dim-label')
        repeat_password_box.append(repeat_password_label)
        
        self.repeat_password_entry = Gtk.PasswordEntry()
        self.repeat_password_entry.set_show_peek_icon(True)
        self.repeat_password_entry.connect("changed", self.validate_fields)
        repeat_password_box.append(self.repeat_password_entry)
        
        self.password_match_error = Gtk.Label(xalign=0)
        self.password_match_error.add_css_class('error')
        self.password_match_error.set_visible(False)
        repeat_password_box.append(self.password_match_error)
        
        # --- System Configuration Section ---
        system_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        form_box.append(system_section)
        
        separator1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        system_section.append(separator1)
        
        system_header = Gtk.Label(label="System Configuration", xalign=0)
        system_header.set_markup('<b>System Configuration</b>')
        system_section.append(system_header)
        
        # Computer Name field
        hostname_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        system_section.append(hostname_box)
        
        hostname_label = Gtk.Label(label="Computer's Name", xalign=0)
        hostname_label.add_css_class('dim-label')
        hostname_box.append(hostname_label)
        
        self.hostname_entry = Gtk.Entry()
        self.hostname_entry.set_text("Linexin-PC")
        self.hostname_entry.connect("changed", self.validate_fields)
        hostname_box.append(self.hostname_entry)
        
        self.hostname_error = Gtk.Label(xalign=0)
        self.hostname_error.add_css_class('error')
        self.hostname_error.set_visible(False)
        hostname_box.append(self.hostname_error)
        
        # --- Root Account Section ---
        root_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        form_box.append(root_section)
        
        separator2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        root_section.append(separator2)
        
        # Root account toggle
        root_toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        root_section.append(root_toggle_box)
        
        root_toggle_label = Gtk.Label(label="Enable Root account?", xalign=0, hexpand=True)
        root_toggle_label.set_markup('<b>Enable Root account?</b>')
        root_toggle_box.append(root_toggle_label)
        
        self.root_switch = Gtk.Switch()
        self.root_switch.set_valign(Gtk.Align.CENTER)
        self.root_switch.connect("notify::active", self.on_root_toggled)
        root_toggle_box.append(self.root_switch)
        
        # Root password fields (initially hidden)
        self.root_fields_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.root_fields_box.set_visible(False)
        root_section.append(self.root_fields_box)
        
        # Root Password field
        root_password_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.root_fields_box.append(root_password_box)
        
        root_password_label = Gtk.Label(label="Root Password", xalign=0)
        root_password_label.add_css_class('dim-label')
        root_password_box.append(root_password_label)
        
        self.root_password_entry = Gtk.PasswordEntry()
        self.root_password_entry.set_show_peek_icon(True)
        self.root_password_entry.connect("changed", self.validate_fields)
        root_password_box.append(self.root_password_entry)
        
        self.root_password_strength = Gtk.Label(xalign=0)
        self.root_password_strength.add_css_class('dim-label')
        root_password_box.append(self.root_password_strength)
        
        # Repeat Root Password field
        repeat_root_password_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.root_fields_box.append(repeat_root_password_box)
        
        repeat_root_password_label = Gtk.Label(label="Repeat Root Password", xalign=0)
        repeat_root_password_label.add_css_class('dim-label')
        repeat_root_password_box.append(repeat_root_password_label)
        
        self.repeat_root_password_entry = Gtk.PasswordEntry()
        self.repeat_root_password_entry.set_show_peek_icon(True)
        self.repeat_root_password_entry.connect("changed", self.validate_fields)
        repeat_root_password_box.append(self.repeat_root_password_entry)
        
        self.root_password_match_error = Gtk.Label(xalign=0)
        self.root_password_match_error.add_css_class('error')
        self.root_password_match_error.set_visible(False)
        repeat_root_password_box.append(self.root_password_match_error)
        
        # --- Navigation Buttons ---
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        self.append(button_box)
        
        self.btn_back = Gtk.Button(label="Back")
        self.btn_back.add_css_class('buttons_all')
        button_box.append(self.btn_back)
        
        self.btn_proceed = Gtk.Button(label="Continue")
        self.btn_proceed.add_css_class('suggested-action')
        self.btn_proceed.add_css_class('buttons_all')
        self.btn_proceed.set_sensitive(False)
        self.btn_proceed.connect("clicked", self.on_continue_clicked)
        button_box.append(self.btn_proceed)
        
        # Initial validation
        self.validate_fields()
    
    def on_root_toggled(self, switch, param):
        """Handle root account toggle."""
        self.root_enabled = switch.get_active()
        self.root_fields_box.set_visible(self.root_enabled)
        
        # Clear root password fields when disabled
        if not self.root_enabled:
            self.root_password_entry.set_text("")
            self.repeat_root_password_entry.set_text("")
        
        self.validate_fields()
    
    def check_password_strength(self, password):
        """Check password strength and return a rating."""
        if not password:
            return "", ""
        
        strength = 0
        feedback = []
        
        if len(password) >= 8:
            strength += 1
        else:
            feedback.append("at least 8 characters")
        
        if re.search(r'[a-z]', password):
            strength += 1
        else:
            feedback.append("lowercase letters")
        
        if re.search(r'[A-Z]', password):
            strength += 1
        else:
            feedback.append("uppercase letters")
        
        if re.search(r'[0-9]', password):
            strength += 1
        else:
            feedback.append("numbers")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            strength += 1
        else:
            feedback.append("special characters")
        
        if strength <= 2:
            color = "red"
            text = "Weak"
        elif strength <= 3:
            color = "orange"
            text = "Fair"
        elif strength <= 4:
            color = "yellow"
            text = "Good"
        else:
            color = "green"
            text = "Strong"
        
        if feedback and strength < 5:
            text += f" (add {', '.join(feedback[:2])})"
        
        return f'<span foreground="{color}">{text}</span>', strength
    
    def validate_username(self, username):
        """Validate username according to Linux standards."""
        if not username:
            return False, "Username is required"
        
        if not re.match(r'^[a-z_][a-z0-9_-]*$', username):
            return False, "Username must start with a letter or underscore, and contain only lowercase letters, numbers, underscores, and hyphens"
        
        if len(username) > 32:
            return False, "Username must be 32 characters or less"
        
        # Check for reserved usernames
        reserved = ['root', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp', 
                   'mail', 'news', 'uucp', 'proxy', 'www-data', 'backup', 'nobody']
        if username in reserved:
            return False, f"'{username}' is a reserved system username"
        
        return True, ""
    
    def validate_hostname(self, hostname):
        """Validate hostname according to RFC standards."""
        if not hostname:
            return False, "Computer name is required"
        
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$', hostname):
            return False, "Computer name must start and end with a letter or number, and contain only letters, numbers, and hyphens"
        
        if len(hostname) > 63:
            return False, "Computer name must be 63 characters or less"
        
        return True, ""
    
    def validate_fields(self, widget=None):
        """Validate all form fields and update UI accordingly."""
        self.validation_errors.clear()
        all_valid = True
        
        # Validate username
        username = self.username_entry.get_text()
        username_valid, username_error = self.validate_username(username)
        if not username_valid:
            self.username_error.set_text(username_error)
            self.username_error.set_visible(True)
            self.validation_errors.add("username")
            all_valid = False
        else:
            self.username_error.set_visible(False)
        
        # Validate hostname
        hostname = self.hostname_entry.get_text()
        hostname_valid, hostname_error = self.validate_hostname(hostname)
        if not hostname_valid:
            self.hostname_error.set_text(hostname_error)
            self.hostname_error.set_visible(True)
            self.validation_errors.add("hostname")
            all_valid = False
        else:
            self.hostname_error.set_visible(False)
        
        # Check user password strength
        user_password = self.password_entry.get_text()
        if user_password:
            strength_text, strength_level = self.check_password_strength(user_password)
            self.password_strength.set_markup(strength_text)
            if strength_level < 2:
                self.validation_errors.add("weak_password")
                all_valid = False
        else:
            self.password_strength.set_text("")
            self.validation_errors.add("no_password")
            all_valid = False
        
        # Check user password match
        repeat_password = self.repeat_password_entry.get_text()
        if user_password and repeat_password and user_password != repeat_password:
            self.password_match_error.set_text("Passwords do not match")
            self.password_match_error.set_visible(True)
            self.validation_errors.add("password_mismatch")
            all_valid = False
        else:
            self.password_match_error.set_visible(False)
        
        # Validate root password if enabled
        if self.root_enabled:
            root_password = self.root_password_entry.get_text()
            if root_password:
                strength_text, strength_level = self.check_password_strength(root_password)
                self.root_password_strength.set_markup(strength_text)
                if strength_level < 2:
                    self.validation_errors.add("weak_root_password")
                    all_valid = False
            else:
                self.root_password_strength.set_text("")
                self.validation_errors.add("no_root_password")
                all_valid = False
            
            # Check root password match
            repeat_root_password = self.repeat_root_password_entry.get_text()
            if root_password and repeat_root_password and root_password != repeat_root_password:
                self.root_password_match_error.set_text("Root passwords do not match")
                self.root_password_match_error.set_visible(True)
                self.validation_errors.add("root_password_mismatch")
                all_valid = False
            else:
                self.root_password_match_error.set_visible(False)
        
        # Check if required fields are filled
        if not self.fullname_entry.get_text():
            all_valid = False
        
        self.btn_proceed.set_sensitive(all_valid)
        return all_valid
    
    def generate_salt(self, length=16):
        """Generate a random salt for password hashing."""
        chars = string.ascii_letters + string.digits + './'
        return ''.join(random.choice(chars) for _ in range(length))
    
    def hash_password(self, password):
        """
        Hash password using SHA512 (standard for modern Linux systems).
        Uses openssl as a fallback if crypt module is not available.
        """
        salt = self.generate_salt()
        
        # Try using openssl command (standard on Arch Linux)
        try:
            result = subprocess.run(
                ['openssl', 'passwd', '-6', '-salt', salt, password],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try using Python's crypt module if available
        try:
            import crypt
            return crypt.crypt(password, f'$6${salt}$')
        except ImportError:
            pass
        
        # Fallback: use a simpler approach for testing
        print("Warning: Using fallback password hashing (less secure)")
        salted = salt + password
        hash_obj = hashlib.sha512(salted.encode())
        return f"$6${salt}${hash_obj.hexdigest()}"
    
    def on_continue_clicked(self, button):
        """Handle the continue button click and generate configuration files."""
        if not self.validate_fields():
            return
        
        # Collect user data
        user_data = {
            'username': self.username_entry.get_text(),
            'fullname': self.fullname_entry.get_text(),
            'password_hash': self.hash_password(self.password_entry.get_text()),
            'hostname': self.hostname_entry.get_text(),
            'root_enabled': self.root_enabled
        }
        
        if self.root_enabled:
            user_data['root_password_hash'] = self.hash_password(self.root_password_entry.get_text())
        
        # Create configuration directory in the specified output location
        config_dir = os.path.join(self.config_output_dir, 'installer_config')
        os.makedirs(config_dir, exist_ok=True)
        
        try:
            # Generate user configuration file
            self.generate_user_config(config_dir, user_data)
            
            # Generate hostname file
            self.generate_hostname_file(config_dir, user_data['hostname'])
            
            # Generate installation script
            self.generate_install_script(config_dir, user_data)
            
            print(f"Configuration files generated successfully in {config_dir}")
            
            # Show success dialog with location
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Success",
                body=f"User configuration has been saved to:\n{config_dir}\n\nMake sure to copy these files to your installation target."
            )
            dialog.add_response("ok", "OK")
            dialog.present()
            
            # Emit signal or callback for next step
            # self.emit('user-created', user_data)
            
        except Exception as e:
            print(f"Error generating configuration files: {e}")
            # Show error dialog
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Error",
                body=f"Failed to generate configuration files: {str(e)}\n\nTry specifying a different output directory with more space."
            )
            dialog.add_response("ok", "OK")
            dialog.present()
    
    def generate_user_config(self, config_dir, user_data):
        """Generate all system files needed for user configuration."""
        
        # Create etc directory structure
        etc_dir = os.path.join(config_dir, 'etc')
        os.makedirs(etc_dir, exist_ok=True)
        os.makedirs(os.path.join(etc_dir, 'sudoers.d'), exist_ok=True)
        
        # Generate /etc/passwd entry
        passwd_file = os.path.join(etc_dir, 'passwd')
        passwd_entry = f"{user_data['username']}:x:1000:1000:{user_data['fullname']}:/home/{user_data['username']}:/bin/bash\n"
        
        # We'll append to existing system users (minimal set)
        with open(passwd_file, 'w') as f:
            # System users (minimal required set)
            f.write("root:x:0:0:root:/root:/bin/bash\n")
            f.write("bin:x:1:1:bin:/bin:/usr/bin/nologin\n")
            f.write("daemon:x:2:2:daemon:/:/usr/bin/nologin\n")
            f.write("mail:x:8:12:mail:/var/spool/mail:/usr/bin/nologin\n")
            f.write("ftp:x:14:11:ftp:/srv/ftp:/usr/bin/nologin\n")
            f.write("http:x:33:33:http:/srv/http:/usr/bin/nologin\n")
            f.write("nobody:x:65534:65534:Nobody:/:/usr/bin/nologin\n")
            f.write("dbus:x:81:81:dbus:/:/usr/bin/nologin\n")
            f.write("systemd-journal:x:190:190:systemd-journal:/:/usr/bin/nologin\n")
            f.write("systemd-network:x:192:192:systemd-network:/:/usr/bin/nologin\n")
            f.write("systemd-resolve:x:193:193:systemd-resolve:/:/usr/bin/nologin\n")
            f.write("systemd-timesync:x:194:194:systemd-timesync:/:/usr/bin/nologin\n")
            f.write("systemd-coredump:x:195:195:systemd-coredump:/:/usr/bin/nologin\n")
            f.write("uuidd:x:68:68:uuidd:/:/usr/bin/nologin\n")
            # Add our user
            f.write(passwd_entry)
        
        # Generate /etc/shadow entry
        shadow_file = os.path.join(etc_dir, 'shadow')
        shadow_entry = f"{user_data['username']}:{user_data['password_hash']}:19000:0:99999:7:::\n"
        
        with open(shadow_file, 'w') as f:
            # System users shadows
            if user_data['root_enabled']:
                f.write(f"root:{user_data['root_password_hash']}:19000:0:99999:7:::\n")
            else:
                f.write("root:!:19000:0:99999:7:::\n")  # Locked root account
            
            f.write("bin:x:19000:0:99999:7:::\n")
            f.write("daemon:x:19000:0:99999:7:::\n")
            f.write("mail:x:19000:0:99999:7:::\n")
            f.write("ftp:x:19000:0:99999:7:::\n")
            f.write("http:x:19000:0:99999:7:::\n")
            f.write("nobody:x:19000:0:99999:7:::\n")
            f.write("dbus:x:19000:0:99999:7:::\n")
            f.write("systemd-journal:x:19000:0:99999:7:::\n")
            f.write("systemd-network:x:19000:0:99999:7:::\n")
            f.write("systemd-resolve:x:19000:0:99999:7:::\n")
            f.write("systemd-timesync:x:19000:0:99999:7:::\n")
            f.write("systemd-coredump:x:19000:0:99999:7:::\n")
            f.write("uuidd:x:19000:0:99999:7:::\n")
            # Add our user
            f.write(shadow_entry)
        
        # Set proper permissions for shadow file
        os.chmod(shadow_file, 0o600)
        
        # Generate /etc/group entries
        group_file = os.path.join(etc_dir, 'group')
        with open(group_file, 'w') as f:
            # System groups
            f.write("root:x:0:root\n")
            f.write("bin:x:1:root,bin,daemon\n")
            f.write("daemon:x:2:root,bin,daemon\n")
            f.write("sys:x:3:root,bin\n")
            f.write("adm:x:4:root,daemon\n")
            f.write("tty:x:5:\n")
            f.write("disk:x:6:root\n")
            f.write("lp:x:7:daemon\n")
            f.write("mem:x:8:\n")
            f.write("kmem:x:9:\n")
            f.write("wheel:x:10:root," + user_data['username'] + "\n")
            f.write("ftp:x:11:\n")
            f.write("mail:x:12:\n")
            f.write("uucp:x:14:\n")
            f.write("log:x:19:root\n")
            f.write("utmp:x:20:\n")
            f.write("locate:x:21:\n")
            f.write("rfkill:x:24:\n")
            f.write("smmsp:x:25:\n")
            f.write("proc:x:26:\n")
            f.write("http:x:33:\n")
            f.write("games:x:50:\n")
            f.write("lock:x:54:\n")
            f.write("uuidd:x:68:\n")
            f.write("dbus:x:81:\n")
            f.write("network:x:90:" + user_data['username'] + "\n")
            f.write("video:x:91:" + user_data['username'] + "\n")
            f.write("audio:x:92:" + user_data['username'] + "\n")
            f.write("optical:x:93:\n")
            f.write("floppy:x:94:\n")
            f.write("storage:x:95:" + user_data['username'] + "\n")
            f.write("scanner:x:96:\n")
            f.write("input:x:97:\n")
            f.write("power:x:98:\n")
            f.write("nobody:x:65534:\n")
            f.write("users:x:1000:" + user_data['username'] + "\n")
            f.write("systemd-journal:x:190:\n")
            f.write("systemd-network:x:192:\n")
            f.write("systemd-resolve:x:193:\n")
            f.write("systemd-timesync:x:194:\n")
            f.write("systemd-coredump:x:195:\n")
            # User's primary group
            f.write(f"{user_data['username']}:x:1000:\n")
        
        # Generate /etc/gshadow
        gshadow_file = os.path.join(etc_dir, 'gshadow')
        with open(gshadow_file, 'w') as f:
            f.write("root:::root\n")
            f.write("wheel:::" + user_data['username'] + "\n")
            f.write("audio:::" + user_data['username'] + "\n")
            f.write("video:::" + user_data['username'] + "\n")
            f.write("network:::" + user_data['username'] + "\n")
            f.write("storage:::" + user_data['username'] + "\n")
            f.write("users:::" + user_data['username'] + "\n")
            f.write(f"{user_data['username']}:!::\n")
        
        os.chmod(gshadow_file, 0o600)
        
        # Generate sudoers file for wheel group
        sudoers_file = os.path.join(etc_dir, 'sudoers.d', '10-installer')
        with open(sudoers_file, 'w') as f:
            f.write("# Created by Linexin Installer\n")
            f.write("%wheel ALL=(ALL:ALL) ALL\n")
        
        os.chmod(sudoers_file, 0o440)
        
        print(f"User system files generated in {etc_dir}")
    
    def generate_hostname_file(self, config_dir, hostname):
        """Generate hostname and hosts files."""
        etc_dir = os.path.join(config_dir, 'etc')
        os.makedirs(etc_dir, exist_ok=True)
        
        # Generate /etc/hostname
        hostname_file = os.path.join(etc_dir, 'hostname')
        with open(hostname_file, 'w') as f:
            f.write(hostname + '\n')
        
        # Generate /etc/hosts
        hosts_file = os.path.join(etc_dir, 'hosts')
        with open(hosts_file, 'w') as f:
            f.write("# Static table lookup for hostnames.\n")
            f.write("# See hosts(5) for details.\n\n")
            f.write("127.0.0.1\tlocalhost\n")
            f.write(f"127.0.1.1\t{hostname}\n")
            f.write("::1\t\tlocalhost\n")
        
        print(f"Hostname files saved to {etc_dir}")
    
    def generate_install_script(self, config_dir, user_data):
        """Generate shell script for copying files to the installed system."""
        script_file = os.path.join(config_dir, 'copy_to_rootfs.sh')
        
        script_content = f"""#!/bin/bash
# Copy user configuration files to installed rootfs
# Generated by Linexin Installer

set -e

ROOTFS_DIR="${{1:-/mnt}}"
CONFIG_DIR="$(dirname "$0")"

if [ ! -d "$ROOTFS_DIR" ]; then
    echo "Error: Root filesystem directory '$ROOTFS_DIR' does not exist!"
    exit 1
fi

echo "Copying user configuration files to rootfs..."

# Backup existing files if they exist
for file in passwd shadow group gshadow hostname hosts; do
    if [ -f "$ROOTFS_DIR/etc/$file" ]; then
        cp "$ROOTFS_DIR/etc/$file" "$ROOTFS_DIR/etc/$file.installer-backup"
    fi
done

# Copy configuration files
cp -v "$CONFIG_DIR/etc/passwd" "$ROOTFS_DIR/etc/"
cp -v "$CONFIG_DIR/etc/shadow" "$ROOTFS_DIR/etc/"
cp -v "$CONFIG_DIR/etc/group" "$ROOTFS_DIR/etc/"
cp -v "$CONFIG_DIR/etc/gshadow" "$ROOTFS_DIR/etc/"
cp -v "$CONFIG_DIR/etc/hostname" "$ROOTFS_DIR/etc/"
cp -v "$CONFIG_DIR/etc/hosts" "$ROOTFS_DIR/etc/"
cp -v "$CONFIG_DIR/etc/sudoers.d/10-installer" "$ROOTFS_DIR/etc/sudoers.d/"

# Set proper permissions
chmod 644 "$ROOTFS_DIR/etc/passwd"
chmod 000 "$ROOTFS_DIR/etc/shadow"
chmod 644 "$ROOTFS_DIR/etc/group"
chmod 000 "$ROOTFS_DIR/etc/gshadow"
chmod 644 "$ROOTFS_DIR/etc/hostname"
chmod 644 "$ROOTFS_DIR/etc/hosts"
chmod 440 "$ROOTFS_DIR/etc/sudoers.d/10-installer"

# Create user home directory
mkdir -p "$ROOTFS_DIR/home/{user_data['username']}"
cp -r "$ROOTFS_DIR/etc/skel/." "$ROOTFS_DIR/home/{user_data['username']}/" 2>/dev/null || true

# Set ownership (will need to be run after chroot or first boot)
echo "Note: File ownership will be set on first boot"

# Create a first-boot script to fix permissions
cat > "$ROOTFS_DIR/etc/systemd/system/first-boot-setup.service" << 'EOF'
[Unit]
Description=First Boot Setup
ConditionPathExists=!/var/lib/first-boot-done
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c "chown -R {user_data['username']}:{user_data['username']} /home/{user_data['username']} && touch /var/lib/first-boot-done"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable the first-boot service
ln -sf /etc/systemd/system/first-boot-setup.service "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants/"

echo "User configuration files copied successfully!"
echo "The system is configured with:"
echo "  Username: {user_data['username']}"
echo "  Hostname: {user_data['hostname']}"
echo "  Root account: {'Enabled' if user_data['root_enabled'] else 'Disabled'}"
"""
        
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_file, 0o755)
        
        print(f"Copy script saved to {script_file}")
    
    def set_config_output_dir(self, directory):
        """Set the output directory for configuration files."""
        if os.path.exists(directory) and os.access(directory, os.W_OK):
            self.config_output_dir = directory
            return True
        else:
            print(f"Warning: Directory {directory} is not writable, using {self.config_output_dir}")
            return False
    
    def get_user_data(self):
        """Public method to get the configured user data."""
        if not self.validate_fields():
            return None
        
        return {
            'username': self.username_entry.get_text(),
            'fullname': self.fullname_entry.get_text(),
            'hostname': self.hostname_entry.get_text(),
            'root_enabled': self.root_enabled
        }


if __name__ == "__main__":
    # Example window to display the widget
    app = Gtk.Application()
    
    def on_activate(app):
        win = Adw.ApplicationWindow(application=app, title="User Creation Test")
        win.set_default_size(600, 800)
        
        # You can specify a custom output directory here
        # For example, if you have a mounted partition at /mnt/install
        # user_widget = UserCreationWidget(config_output_dir="/mnt/install")
        
        # Or use the default /tmp directory
        user_widget = UserCreationWidget()
        
        # Or set it after creation
        # user_widget.set_config_output_dir("/path/to/mounted/partition")
        
        # Example callback for back button
        def on_back():
            print("Back button clicked")
        
        user_widget.btn_back.connect("clicked", lambda x: on_back())
        
        win.set_content(user_widget)
        win.present()
    
    app.connect('activate', on_activate)
    app.run(None)