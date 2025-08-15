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
        if self.save_locale_config():
            print(f"Locale configuration saved for: {self.get_selected_language_code()}")
            # You can add navigation to the next widget here
        else:
            print("Failed to save locale configuration")

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

    def save_locale_config(self):
        """Save the selected locale configuration to /tmp/installer_config/etc/locale.conf"""
        selected_locale = self.get_selected_language_code()
        if not selected_locale:
            return False
        
        try:
            import os
            
            # Create directory structure in /tmp/installer_config/etc/
            etc_dir = "/tmp/installer_config/etc"
            os.makedirs(etc_dir, exist_ok=True)
            
            # Create locale.conf content
            locale_content = [
                f"LANG={selected_locale}",
                f"LC_ADDRESS={selected_locale}",
                f"LC_IDENTIFICATION={selected_locale}",
                f"LC_MEASUREMENT={selected_locale}",
                f"LC_MONETARY={selected_locale}",
                f"LC_NAME={selected_locale}",
                f"LC_NUMERIC={selected_locale}",
                f"LC_PAPER={selected_locale}",
                f"LC_TELEPHONE={selected_locale}",
                f"LC_TIME={selected_locale}"
            ]
            
            # Save locale.conf to /tmp/installer_config/etc/
            locale_conf_path = os.path.join(etc_dir, "locale.conf")
            
            with open(locale_conf_path, 'w') as f:
                f.write('\n'.join(locale_content) + '\n')
            
            print(f"Locale configuration saved to: {locale_conf_path}")
            return True
            
        except Exception as e:
            print(f"Error saving locale configuration: {e}")
            return False    

    def on_search_changed(self, entry):
        search_text = entry.get_text().lower()
        # Iterate through all rows and set their visibility based on the search term
        for row in self.language_rows:
            row.set_visible(search_text in row.search_term)

    def on_row_selected(self, listbox, row):
        """Updated to save locale config when a language is selected"""
        self.btn_proceed.set_sensitive(row is not None)
        
        # Save locale configuration when a language is selected
        if row is not None:
            self.save_locale_config()

    def get_locale_config_path(self):
        """Get the path to the generated locale.conf file"""
        return "/tmp/installer_config/etc/locale.conf"

    def get_selected_language_code(self):
        selected_row = self.list_box.get_selected_row()
        if selected_row:
            return selected_row.locale_code
        return None

    def apply_locale_to_system(self):
        """Apply the generated locale.conf to the system (optional method for testing)"""
        try:
            import subprocess
            import os
            from datetime import datetime
            
            locale_conf_path = self.get_locale_config_path()
            if not os.path.exists(locale_conf_path):
                print("No locale.conf found in /tmp/installer_config/etc/")
                return False
            
            # Create backup of current /etc/locale.conf if it exists
            if os.path.exists("/etc/locale.conf"):
                backup_path = f"/etc/locale.conf.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                cmd = ['sudo', 'cp', '/etc/locale.conf', backup_path]
                subprocess.run(cmd, check=True, timeout=10)
                print(f"Backed up /etc/locale.conf to {backup_path}")
            
            # Copy generated locale.conf to /etc/locale.conf
            cmd = ['sudo', 'cp', locale_conf_path, '/etc/locale.conf']
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if process.returncode != 0:
                print(f"Failed to copy locale.conf to /etc/locale.conf: {process.stderr}")
                return False
            else:
                print("Successfully updated /etc/locale.conf")
                return True
                
        except Exception as e:
            print(f"Error applying locale.conf to system: {e}")
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
