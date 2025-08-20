#!/usr/bin/env python3

import gi
import locale
import gettext

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

class LanguageWidget(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(20)
        self.set_margin_top(30)
        self.set_margin_bottom(30)
        
        # A list to hold the language row widgets for easy filtering
        self.language_rows = []

        # --- UI Elements ---

        # Main title label
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Select a Language</span>")
        title.set_halign(Gtk.Align.CENTER)
        self.append(title)

        # --- Adw.Clamp constrains the width of the content ---
        clamp = Adw.Clamp(margin_start=12, margin_end=12, maximum_size=600)
        clamp.set_vexpand(True)
        self.append(clamp)

        # A content box to hold the search and list inside the clamp
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        clamp.set_child(content_box)

        # Search entry to filter languages
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search for a language...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        content_box.append(self.search_entry)

        # ScrolledWindow to contain the list of languages
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_has_frame(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        content_box.append(scrolled_window)

        # ListBox to display each language
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.get_style_context().add_class("boxed-list")
        scrolled_window.set_child(self.list_box)

        # Populate the list with available languages
        self.populate_languages()

        # Action bar at the bottom for navigation buttons
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_bar.set_halign(Gtk.Align.CENTER)
        self.append(action_bar)

        # The "Back" button
        self.btn_back = Gtk.Button(label="Back")
        self.btn_back.add_css_class("buttons_all")
        action_bar.append(self.btn_back)


        # The "Proceed" button
        self.btn_proceed = Gtk.Button(label="Continue")
        self.btn_proceed.add_css_class("suggested-action")
        self.btn_proceed.add_css_class("buttons_all")
        self.btn_proceed.set_sensitive(False) 
        action_bar.append(self.btn_proceed)

        # Connect signal to enable the proceed button upon selection
        self.list_box.connect("row-selected", self.on_row_selected)

    def on_continue_clicked(self, button):
        """Handle the Continue button click"""
        if self.create_language_script():
            print(f"Language script created for: {self.get_selected_language_code()}")
            # You can add navigation to the next widget here
        else:
            print("Failed to create language script")

    def country_code_to_emoji(self, country_code):
        """Converts a two-letter country code to a flag emoji."""
        # Formula to convert a two-letter country code to a flag emoji
        # (e.g., 'US' -> '🇺🇸')
        if len(country_code) != 2:
            return "🏳️" # Return a white flag for invalid codes
        
        return "".join(chr(ord(char) - ord('A') + 0x1F1E6) for char in country_code.upper())

    def populate_languages(self):
        # A comprehensive list of languages.
        languages = {
            "af_ZA.UTF-8": "Afrikaans (South Africa)", "sq_AL.UTF-8": "Albanian (Albania)",
            "ar_SA.UTF-8": "Arabic (Saudi Arabia)", "be_BY.UTF-8": "Belarusian (Belarus)",
            "bs_BA.UTF-8": "Bosnian (Bosnia and Herzegovina)", "bg_BG.UTF-8": "Bulgarian (Bulgaria)",
            "ca_ES.UTF-8": "Catalan (Spain)", "zh_CN.UTF-8": "Chinese (Simplified, China)",
            "zh_TW.UTF-8": "Chinese (Traditional, Taiwan)", "hr_HR.UTF-8": "Croatian (Croatia)",
            "cs_CZ.UTF-8": "Czech (Czech Republic)", "da_DK.UTF-8": "Danish (Denmark)",
            "nl_NL.UTF-8": "Dutch (Netherlands)", "en_US.UTF-8": "English (United States)",
            "en_GB.UTF-8": "English (United Kingdom)", "en_AU.UTF-8": "English (Australia)",
            "en_CA.UTF-8": "English (Canada)", "et_EE.UTF-8": "Estonian (Estonia)",
            "fa_IR.UTF-8": "Farsi (Iran)", "fil_PH.UTF-8": "Filipino (Philippines)",
            "fi_FI.UTF-8": "Finnish (Finland)", "fr_FR.UTF-8": "French (France)",
            "fr_CA.UTF-8": "French (Canada)", "ga_IE.UTF-8": "Gaelic (Ireland)",
            "gl_ES.UTF-8": "Galician (Spain)", "ka_GE.UTF-8": "Georgian (Georgia)",
            "de_DE.UTF-8": "German (Germany)", "el_GR.UTF-8": "Greek (Greece)",
            "gu_IN.UTF-8": "Gujarati (India)", "he_IL.UTF-8": "Hebrew (Israel)",
            "hi_IN.UTF-8": "Hindi (India)", "hu_HU.UTF-8": "Hungarian (Hungary)",
            "is_IS.UTF-8": "Icelandic (Iceland)", "id_ID.UTF-8": "Indonesian (Indonesia)",
            "it_IT.UTF-8": "Italian (Italy)", "ja_JP.UTF-8": "Japanese (Japan)",
            "kn_IN.UTF-8": "Kannada (India)", "km_KH.UTF-8": "Khmer (Cambodia)",
            "ko_KR.UTF-8": "Korean (Korea)", "lo_LA.UTF-8": "Lao (Laos)",
            "lt_LT.UTF-8": "Lithuanian (Lithuania)", "lv_LV.UTF-8": "Latvian (Latvia)",
            "ml_IN.UTF-8": "Malayalam (India)", "ms_MY.UTF-8": "Malaysian (Malaysia)",
            "mi_NZ.UTF-8": "Maori (New Zealand)", "mn_MN.UTF-8": "Mongolian (Mongolia)",
            "no_NO.UTF-8": "Norwegian (Norway)", "nn_NO.UTF-8": "Norwegian (Nynorsk, Norway)",
            "pl_PL.UTF-8": "Polish (Poland)", "pt_PT.UTF-8": "Portuguese (Portugal)",
            "pt_BR.UTF-8": "Portuguese (Brazil)", "ro_RO.UTF-8": "Romanian (Romania)",
            "ru_RU.UTF-8": "Russian (Russia)", "sr_RS.UTF-8": "Serbian (Serbia)",
            "sk_SK.UTF-8": "Slovak (Slovakia)", "sl_SI.UTF-8": "Slovenian (Slovenia)",
            "so_SO.UTF-8": "Somali (Somalia)", "es_ES.UTF-8": "Spanish (Spain)",
            "sv_SE.UTF-8": "Swedish (Sweden)", "tl_PH.UTF-8": "Tagalog (Philippines)",
            "ta_IN.UTF-8": "Tamil (India)", "th_TH.UTF-8": "Thai (Thailand)",
            "tr_TR.UTF-8": "Turkish (Turkey)", "uk_UA.UTF-8": "Ukrainian (Ukraine)",
            "vi_VN.UTF-8": "Vietnamese (Vietnam)",
        }

        # Sort languages alphabetically by name
        for code, name in sorted(languages.items(), key=lambda item: item[1]):
            # --- FIX: Use a simple Gtk.ListBoxRow with a Gtk.Label ---
            row = Gtk.ListBoxRow()
            
            # --- FEATURE: Add flag emoji ---
            country_code = code.split('_')[1].split('.')[0]
            flag_emoji = self.country_code_to_emoji(country_code)
            
            label = Gtk.Label(label=f"{flag_emoji} {name}", xalign=0, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
            row.set_child(label)
            
            # Attach metadata to the row for later use
            row.locale_code = code
            row.search_term = name.lower() # Store a lowercase version for searching
            
            self.list_box.append(row)
            self.language_rows.append(row)

    def create_language_script(self):
        """Create a bash script to configure the system language"""
        selected_locale = self.get_selected_language_code()
        if not selected_locale:
            return False
        
        try:
            import os
            
            # Create directory structure in /tmp/installer_config/
            config_dir = "/tmp/installer_config"
            os.makedirs(config_dir, exist_ok=True)
            
            # Create the bash script content
            script_content = f'''#!/bin/bash
# Language configuration script generated by installer
# This script configures the system locale to {selected_locale}
# Designed to run in arch-chroot environment as root

set -e  # Exit on any error

echo "Configuring system locale to {selected_locale}..."
echo "Running in arch-chroot environment as root"

# Backup existing configurations
backup_configs() {{
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [[ -f /etc/locale.conf ]]; then
        echo "Backing up /etc/locale.conf..."
        cp /etc/locale.conf "/etc/locale.conf.backup.$timestamp"
    fi
    
    if [[ -f /etc/locale.gen ]]; then
        echo "Backing up /etc/locale.gen..."
        cp /etc/locale.gen "/etc/locale.gen.backup.$timestamp"
    fi
}}

# Generate locale.gen file
generate_locale_gen() {{
    echo "Generating /etc/locale.gen..."
    cat > /etc/locale.gen << 'EOL'
# Locale configuration generated by installer
# Always include en_US.UTF-8 as fallback
en_US.UTF-8 UTF-8
{selected_locale} UTF-8
EOL
    echo "✓ /etc/locale.gen created"
}}

# Generate locale.conf file
generate_locale_conf() {{
    echo "Generating /etc/locale.conf..."
    cat > /etc/locale.conf << 'EOL'
LANG={selected_locale}
LC_ADDRESS={selected_locale}
LC_IDENTIFICATION={selected_locale}
LC_MEASUREMENT={selected_locale}
LC_MONETARY={selected_locale}
LC_NAME={selected_locale}
LC_NUMERIC={selected_locale}
LC_PAPER={selected_locale}
LC_TELEPHONE={selected_locale}
LC_TIME={selected_locale}
LC_COLLATE={selected_locale}
LC_CTYPE={selected_locale}
LC_MESSAGES={selected_locale}
EOL
    echo "✓ /etc/locale.conf created"
}}

# Generate locales
generate_locales() {{
    echo "Generating locales (this may take a moment)..."
    if command -v locale-gen &> /dev/null; then
        locale-gen
        echo "✓ Locales generated successfully"
    else
        echo "⚠️  locale-gen not found, locales will be generated on first boot"
    fi
}}

# Create systemd locale environment file
create_systemd_locale() {{
    echo "Creating systemd locale configuration..."
    mkdir -p /etc/systemd/system.conf.d
    cat > /etc/systemd/system.conf.d/10-locale.conf << 'EOL'
[Manager]
DefaultEnvironment="LANG={selected_locale}" "LC_ALL={selected_locale}"
EOL
    echo "✓ Systemd locale configuration created"
}}

# Update environment for future users
setup_default_environment() {{
    echo "Setting up default environment..."
    
    # Create /etc/environment for system-wide locale
    cat > /etc/environment << 'EOL'
LANG={selected_locale}
LC_ALL={selected_locale}
EOL
    echo "✓ /etc/environment created"
    
    # Create default shell configuration
    mkdir -p /etc/skel
    
    # Add locale to default .bashrc for new users
    if [[ ! -f /etc/skel/.bashrc ]] || ! grep -q "LANG=" /etc/skel/.bashrc; then
        cat >> /etc/skel/.bashrc << 'EOL'

# Locale configuration
export LANG={selected_locale}
export LC_ALL={selected_locale}
EOL
        echo "✓ Default .bashrc updated with locale"
    fi
    
    # Add locale to default .profile for new users
    if [[ ! -f /etc/skel/.profile ]] || ! grep -q "LANG=" /etc/skel/.profile; then
        cat >> /etc/skel/.profile << 'EOL'

# Locale configuration
export LANG={selected_locale}
export LC_ALL={selected_locale}
EOL
        echo "✓ Default .profile updated with locale"
    fi
}}

# Update existing user directories (if any exist in chroot)
update_existing_users() {{
    echo "Updating existing user environments..."
    
    # Find user home directories (excluding system users)
    local updated_users=0
    
    for user_home in /home/*; do
        if [[ -d "$user_home" ]]; then
            local username=$(basename "$user_home")
            echo "Updating environment for user: $username"
            
            # Update .bashrc
            if [[ -f "$user_home/.bashrc" ]]; then
                # Remove existing locale exports
                sed -i '/^export LANG=/d' "$user_home/.bashrc"
                sed -i '/^export LC_/d' "$user_home/.bashrc"
                
                # Add new locale exports
                cat >> "$user_home/.bashrc" << 'EOL'

# Locale configuration (updated by installer)
export LANG={selected_locale}
export LC_ALL={selected_locale}
EOL
                echo "  ✓ Updated $user_home/.bashrc"
            fi
            
            # Update .profile
            if [[ -f "$user_home/.profile" ]]; then
                # Remove existing locale exports
                sed -i '/^export LANG=/d' "$user_home/.profile"
                sed -i '/^export LC_/d' "$user_home/.profile"
                
                # Add new locale exports
                cat >> "$user_home/.profile" << 'EOL'

# Locale configuration (updated by installer)
export LANG={selected_locale}
export LC_ALL={selected_locale}
EOL
                echo "  ✓ Updated $user_home/.profile"
            fi
            
            updated_users=$((updated_users + 1))
        fi
    done
    
    if [[ $updated_users -eq 0 ]]; then
        echo "No existing user directories found"
    else
        echo "✓ Updated $updated_users user environment(s)"
    fi
}}

# Verify locale configuration
verify_configuration() {{
    echo ""
    echo "Verifying locale configuration..."
    
    if [[ -f /etc/locale.conf ]]; then
        echo "✓ /etc/locale.conf exists"
        if grep -q "{selected_locale}" /etc/locale.conf; then
            echo "✓ Locale {selected_locale} found in /etc/locale.conf"
        fi
    fi
    
    if [[ -f /etc/locale.gen ]]; then
        echo "✓ /etc/locale.gen exists"
        if grep -q "{selected_locale}" /etc/locale.gen; then
            echo "✓ Locale {selected_locale} found in /etc/locale.gen"
        fi
    fi
    
    if [[ -f /etc/environment ]]; then
        echo "✓ /etc/environment exists"
    fi
}}

# Main execution
main() {{
    echo "============================================="
    echo "  Arch Linux Language Configuration Script"
    echo "============================================="
    echo "Selected locale: {selected_locale}"
    echo "Execution environment: arch-chroot (root)"
    echo ""
    
    # Verify we're running as root
    if [[ $EUID -ne 0 ]]; then
        echo "❌ This script must be run as root (in arch-chroot)"
        exit 1
    fi
    
    backup_configs
    generate_locale_gen
    generate_locale_conf
    generate_locales
    create_systemd_locale
    setup_default_environment
    update_existing_users
    verify_configuration
    
    echo ""
    echo "🎉 Language configuration completed successfully!"
    echo "Selected locale: {selected_locale}"
    echo ""
    echo "📋 Configuration summary:"
    echo "  • /etc/locale.conf - System locale configuration"
    echo "  • /etc/locale.gen - Locale generation list"
    echo "  • /etc/environment - System-wide environment"
    echo "  • /etc/systemd/system.conf.d/10-locale.conf - Systemd locale"
    echo "  • /etc/skel/.bashrc and .profile - Default user environment"
    echo ""
    echo "✅ The system will use {selected_locale} after the next boot"
    echo ""
}}

# Run the main function
main "$@"
'''
            
            # Save the script
            script_path = os.path.join(config_dir, "language.sh")
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make the script executable
            os.chmod(script_path, 0o755)
            
            print(f"Language configuration script created at: {script_path}")
            return True
            
        except Exception as e:
            print(f"Error creating language script: {e}")
            return False

    def on_search_changed(self, entry):
        search_text = entry.get_text().lower()
        # Iterate through all rows and set their visibility based on the search term
        for row in self.language_rows:
            row.set_visible(search_text in row.search_term)

    def on_row_selected(self, listbox, row):
        """Updated to create language script when a language is selected"""
        self.btn_proceed.set_sensitive(row is not None)
        
        # Create language script when a language is selected
        if row is not None:
            self.create_language_script()

    def get_script_path(self):
        """Get the path to the generated language script"""
        return "/tmp/installer_config/language.sh"

    def get_selected_language_code(self):
        selected_row = self.list_box.get_selected_row()
        if selected_row:
            return selected_row.locale_code
        return None

    def execute_language_script(self):
        """Execute the generated language script"""
        try:
            import subprocess
            import os
            
            script_path = self.get_script_path()
            
            if not os.path.exists(script_path):
                print("Language script not found. Please select a language first.")
                return False
            
            if not os.access(script_path, os.X_OK):
                print("Language script is not executable. Making it executable...")
                os.chmod(script_path, 0o755)
            
            print(f"Executing language configuration script: {script_path}")
            print("This may require sudo privileges...")
            
            # Execute the script
            process = subprocess.Popen(
                [script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Print output in real-time
            for line in process.stdout:
                print(line.rstrip())
            
            # Wait for completion and get return code
            process.wait()
            
            if process.returncode == 0:
                print("✅ Language configuration script executed successfully!")
                return True
            else:
                stderr_output = process.stderr.read()
                print(f"❌ Script execution failed with return code: {process.returncode}")
                if stderr_output:
                    print(f"Error output: {stderr_output}")
                return False
                
        except Exception as e:
            print(f"Error executing language script: {e}")
            return False

if __name__ == "__main__":
    # Example window to display the widget
    app = Gtk.Application()
    def on_activate(app):
        win = Adw.ApplicationWindow(application=app, title="Language Selector Test")
        win.set_default_size(500, 700)
        lang_widget = LanguageWidget()
        win.set_content(lang_widget)
        win.present()
    app.connect('activate', on_activate)
    app.run(None)