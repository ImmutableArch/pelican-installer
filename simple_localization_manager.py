#!/usr/bin/env python3

import json
import os
from gi.repository import GObject, Gtk, Adw

class SimpleLocalizationManager(GObject.Object):
    """
    A simple localization manager that automatically finds and updates
    translatable elements without requiring manual registration.
    """
    
    __gtype_name__ = 'SimpleLocalizationManager'
    
    # Signal emitted when language changes
    __gsignals__ = {
        'language-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self.current_language = "en_US.UTF-8"
        self.translations = {}
        self.registered_widgets = []  # Keep track of top-level widgets
        self.load_translations()
        self._initialized = True
    
    def load_translations(self):
        """Load translation data - same as before but with translation keys matching UI text"""
        
        self.translations["en_US.UTF-8"] = {
            # Exact text matching (what appears in your UI)

            #Language
            "Select a Language": "Select a Language",
            "Search for a language...": "Search for a language...",
            "Back": "Back",
            "Continue": "Continue",

            #Timezone
            "Select Your Timezone": "Select Your Timezone",
            "Choose a city in your region. This will be used to set the clock.": "Choose a city in your region. This will be used to set the clock.",
            "Search for your city or region...": "Search for your city or region...",
            "Advanced": "Advanced",
            "Proceed": "Proceed",
            "Cancel": "Cancel",
            "Next": "Next",
            "Previous": "Previous",
            "Finish": "Finish",

            #Keyboard
            "Select Your Keyboard Layout": "Select Your Keyboard Layout",
            "Test your layout here:": "Test your layout here:",
            "You can add more after installation.": "You can add more after installation.",


            # Disk Utility Widget
            "Select a disk": "Select a disk",
            "Click on a disk or partition to select it or modify it.": "Click on a disk or partition to select it or modify it.",
            "No Disks Found": "No Disks Found",
            "Size": "Size",
            "Type": "Type",
            "Mount": "Mount",
            "Bootable": "Bootable",
            "Not configured": "Not configured",
            "Unallocated": "Unallocated",
            "Free Space": "Free Space",
            "Back": "Back",
            "Add": "Add",
            "Remove": "Remove",
            "Format": "Format",
            "Auto": "Auto",
            "Filesystem": "Filesystem",
            "Mountpoint": "Mountpoint",
            "Boot flag": "Boot flag",
            "Continue": "Continue",
            "Selected": "Selected",
            "Loading...": "Loading...",
            "Scanning for storage devices.": "Scanning for storage devices.",
            "Waiting for Gparted": "Waiting for Gparted",
            "The disk list will be refreshed after you close the Gparted application.": "The disk list will be refreshed after you close the Gparted application.",
            "Error: Gparted Not Found": "Error: Gparted Not Found",
            "Could not launch Gparted": "Could not launch Gparted",
            "OK": "OK",
            
            # Dialog titles and messages
            "Missing Required Configuration": "Missing Required Configuration",
            "No bootable partition found": "No bootable partition found",
            "No root (/) mountpoint configured": "No root (/) mountpoint configured",
            "Would you like to automatically configure the selected device?": "Would you like to automatically configure the selected device?",
            "Auto-configure will:": "Auto-configure will:",
            "Remove the selected partition/disk": "Remove the selected partition/disk",
            "Create a 1GB FAT32 boot partition at /boot": "Create a 1GB FAT32 boot partition at /boot",
            "Create an ext4 root partition at / with remaining space": "Create an ext4 root partition at / with remaining space",
            "WARNING: All data on the selected device will be lost!": "WARNING: All data on the selected device will be lost!",
            "Go Back": "Go Back",
            "Continue Anyway": "Continue Anyway",
            "Auto-Configure": "Auto-Configure",
            "Configuration Required": "Configuration Required",
            "Please select a disk and configure:": "Please select a disk and configure:",
            "At least one bootable partition": "At least one bootable partition",
            "A root (/) mountpoint": "A root (/) mountpoint",
            
            # Progress and status messages
            "Auto-Configuring": "Auto-Configuring",
            "Setting up UEFI boot and root partitions...": "Setting up UEFI boot and root partitions...",
            "Setting up Legacy boot and root partitions...": "Setting up Legacy boot and root partitions...",
            "Formatting Disk": "Formatting Disk",
            "Wiping disk and creating UEFI partitions...": "Wiping disk and creating UEFI partitions...",
            "Wiping disk and creating Legacy partitions...": "Wiping disk and creating Legacy partitions...",
            "Success": "Success",
            "UEFI disk configured successfully!": "UEFI disk configured successfully!",
            "Created partitions:": "Created partitions:",
            "1 GiB FAT32 at /boot (ESP)": "1 GiB FAT32 at /boot (ESP)",
            "ext4 at /": "ext4 at /",
            "fstab has been updated.": "fstab has been updated.",
            "Legacy disk configured successfully!": "Legacy disk configured successfully!",
            "ext4 at / (bootable)": "ext4 at / (bootable)",
            "Note: GRUB will be installed to the MBR of": "Note: GRUB will be installed to the MBR of",
            "Error": "Error",
            
            # Partition operations
            "Remove Partition": "Remove Partition",
            "Are you sure you want to remove partition": "Are you sure you want to remove partition",
            "This action cannot be undone and all data will be lost!": "This action cannot be undone and all data will be lost!",
            "Cancel": "Cancel",
            "Format Partition": "Format Partition",
            "Select filesystem type for": "Select filesystem type for",
            "Warning: All data will be lost!": "Warning: All data will be lost!",
            "ext4": "ext4",
            "Btrfs": "Btrfs",
            "NTFS": "NTFS",
            "FAT32": "FAT32",
            "exFAT": "exFAT",
            "swap": "swap",
            "Unformatted": "Unformatted",
            
            # Installation Widget
            "Installing System": "Installing System",
            "Preparing installation...": "Preparing installation...",
            "Please wait while the system prepares for installation": "Please wait while the system prepares for installation",
            "Step": "Step",
            "of": "of",
            "Elapsed time": "Elapsed time",
            "Show Details": "Show Details",
            "Hide Details": "Hide Details",
            "Cancel Installation?": "Cancel Installation?",
            "Are you sure you want to cancel the installation? This may leave your system in an incomplete state.": "Are you sure you want to cancel the installation? This may leave your system in an incomplete state.",
            "Keep Installing": "Keep Installing",
            "Cancel Installation": "Cancel Installation",
            "Cancelling installation...": "Cancelling installation...",
            "Installation Complete!": "Installation Complete!",
            "System installed successfully": "System installed successfully",
            "Your system has been installed and is ready to use.": "Your system has been installed and is ready to use.",
            "Finish": "Finish",
            "Installation Failed": "Installation Failed",
            "An error occurred during installation": "An error occurred during installation",
            "Try Again": "Try Again",
            "Installation Cancelled": "Installation Cancelled",
            "Installation was cancelled by user": "Installation was cancelled by user",
            "The installation process was interrupted.": "The installation process was interrupted.",
            "Restart": "Restart",
            "INSTALLATION COMPLETED SUCCESSFULLY!": "INSTALLATION COMPLETED SUCCESSFULLY!",
            
            # Installation steps
            "Creating installation directories": "Creating installation directories",
            "Setting up temporary installation directories": "Setting up temporary installation directories",
            "Mounting installation image": "Mounting installation image",
            "containing the system image": "containing the system image",
            "Mounting root partition": "Mounting root partition",
            "Mounting the root partition based on /etc/fstab": "Mounting the root partition based on /etc/fstab",
            "Creating boot directory": "Creating boot directory",
            "Creating boot mount point": "Creating boot mount point",
            "Mounting boot partition": "Mounting boot partition",
            "Mounting the boot partition based on /etc/fstab": "Mounting the boot partition based on /etc/fstab",
            "Copying system files": "Copying system files",
            "Copying the system image to your disk. This may take several minutes...": "Copying the system image to your disk. This may take several minutes...",
            "Verifying file copy": "Verifying file copy",
            "Verifying that files were copied successfully": "Verifying that files were copied successfully",
            "Removing live ISO fstab": "Removing live ISO fstab",
            "Removing the live ISO filesystem configuration": "Removing the live ISO filesystem configuration",
            "Applying installer configuration": "Applying installer configuration",
            "Copying installer configuration files to the new system": "Copying installer configuration files to the new system",
            "Removing wheel sudo configuration": "Removing wheel sudo configuration",
            "Removing temporary sudo configuration": "Removing temporary sudo configuration",
            "Changing system's language": "Changing system's language",
            "Changing system's language to a selected one": "Changing system's language to a selected one",
            "Setting up timezone": "Setting up timezone",
            "Linking timezone to the selected one in the installer": "Linking timezone to the selected one in the installer",
            "Setting up keyboard layout": "Setting up keyboard layout",
            "Using proper commands in chroot environment to set up keyboard layout": "Using proper commands in chroot environment to set up keyboard layout",
            "Adding user": "Adding user",
            "Adding user, setting it's password and hostname for the PC": "Adding user, setting it's password and hostname for the PC",
            "Cleaning out rootfs": "Cleaning out rootfs",
            "Cleaning out rootfs from LiveISO's config and applying post-install scripts": "Cleaning out rootfs from LiveISO's config and applying post-install scripts",
            "Installing bootloader": "Installing bootloader",
            "Checking for other systems installed and installing proper bootloader": "Checking for other systems installed and installing proper bootloader",
            "Unmounting filesystems": "Unmounting filesystems",
            "Safely unmounting all filesystems": "Safely unmounting all filesystems",
            
            # Finish Widget
            "Installation has finished successfully!": "Installation has finished successfully!",
            "Everything is set up for you. Thank you for choosing LineXin.": "Everything is set up for you. Thank you for choosing LineXin.",
            "Reboot the system to finish installation.": "Reboot the system to finish installation.",
            "Reboot": "Reboot",
            "Reboot System": "Reboot System",
            "Are you sure you want to reboot now?": "Are you sure you want to reboot now?",
            "Reboot Failed": "Reboot Failed",
            "Could not reboot the system. Please reboot manually.": "Could not reboot the system. Please reboot manually.",
            "Installation Complete": "Installation Complete"

        }
        
        self.translations["pl_PL.UTF-8"] = {
            #Language
            "Select a Language": "Wybierz język",
            "Search for a language...": "Szukaj języka...",
            "Back": "Wróć",
            "Continue": "Kontynuuj",

            #Timezone
            "Select Your Timezone": "Wybierz swoją strefę czasową",
            "Choose a city in your region. This will be used to set the clock.": "Wybierz miasto w swoim regionie. Zostanie ono użyte do ustawienia zegara.",
            "Search for your city or region...": "Szukaj miasta lub regionu...",
            "Advanced": "Zaawansowane",
            "Proceed": "Dalej",
            "Cancel": "Anuluj",
            "Next": "Dalej",
            "Previous": "Wstecz",
            "Finish": "Zakończ",

            #Keyboard
            "Select Your Keyboard Layout": "Wybierz układ klawiatury",
            "Test your layout here:": "Przetestuj układ tutaj:",
            "You can add more after installation.": "Możesz dodać więcej po instalacji.",

            # Disk Utility Widget
            "Select a disk": "Wybierz dysk",
            "Click on a disk or partition to select it or modify it.": "Kliknij dysk lub partycję, aby wybrać lub zmodyfikować.",
            "No Disks Found": "Nie znaleziono dysków",
            "Size": "Rozmiar",
            "Type": "Typ",
            "Mount": "Montowanie",
            "Bootable": "Startowy",
            "Not configured": "Nieskonfigurowane",
            "Unallocated": "Niezajęte",
            "Free Space": "Wolne miejsce",
            "Back": "Wróć",
            "Add": "Dodaj",
            "Remove": "Usuń",
            "Format": "Formatuj",
            "Auto": "Automatycznie",
            "Filesystem": "System plików",
            "Mountpoint": "Punkt montowania",
            "Boot flag": "Flaga startowa",
            "Continue": "Kontynuuj",
            "Selected": "Wybrano",
            "Loading...": "Ładowanie...",
            "Scanning for storage devices.": "Wyszukiwanie urządzeń pamięci masowej.",
            "Waiting for Gparted": "Oczekiwanie na Gparted",
            "The disk list will be refreshed after you close the Gparted application.": "Lista dysków zostanie odświeżona po zamknięciu aplikacji Gparted.",
            "Error: Gparted Not Found": "Błąd: nie znaleziono Gparted",
            "Could not launch Gparted": "Nie można uruchomić Gparted",
            "OK": "OK",
            
            # Dialog titles and messages
            "Missing Required Configuration": "Brak wymaganej konfiguracji",
            "No bootable partition found": "Nie znaleziono partycji startowej",
            "No root (/) mountpoint configured": "Nie skonfigurowano punktu montowania root (/)",
            "Would you like to automatically configure the selected device?": "Czy chcesz automatycznie skonfigurować wybrane urządzenie?",
            "Auto-configure will:": "Automatyczna konfiguracja wykona:",
            "Remove the selected partition/disk": "Usunięcie wybranej partycji/dysku",
            "Create a 1GB FAT32 boot partition at /boot": "Utworzenie partycji rozruchowej FAT32 1 GB w /boot",
            "Create an ext4 root partition at / with remaining space": "Utworzenie partycji root ext4 w / z pozostałym miejscem",
            "WARNING: All data on the selected device will be lost!": "OSTRZEŻENIE: wszystkie dane na wybranym urządzeniu zostaną utracone!",
            "Go Back": "Wróć",
            "Continue Anyway": "Kontynuuj mimo to",
            "Auto-Configure": "Skonfiguruj automatycznie",
            "Configuration Required": "Wymagana konfiguracja",
            "Please select a disk and configure:": "Wybierz dysk i skonfiguruj:",
            "At least one bootable partition": "Przynajmniej jedna partycja startowa",
            "A root (/) mountpoint": "Punkt montowania root (/)",
            
            # Progress and status messages
            "Auto-Configuring": "Automatyczna konfiguracja",
            "Setting up UEFI boot and root partitions...": "Konfigurowanie partycji UEFI boot i root...",
            "Setting up Legacy boot and root partitions...": "Konfigurowanie partycji Legacy boot i root...",
            "Formatting Disk": "Formatowanie dysku",
            "Wiping disk and creating UEFI partitions...": "Czyszczenie dysku i tworzenie partycji UEFI...",
            "Wiping disk and creating Legacy partitions...": "Czyszczenie dysku i tworzenie partycji Legacy...",
            "Success": "Sukces",
            "UEFI disk configured successfully!": "Dysk UEFI został pomyślnie skonfigurowany!",
            "Created partitions:": "Utworzone partycje:",
            "1 GiB FAT32 at /boot (ESP)": "1 GiB FAT32 w /boot (ESP)",
            "ext4 at /": "ext4 w /",
            "fstab has been updated.": "Plik fstab został zaktualizowany.",
            "Legacy disk configured successfully!": "Dysk Legacy został pomyślnie skonfigurowany!",
            "ext4 at / (bootable)": "ext4 w / (startowy)",
            "Note: GRUB will be installed to the MBR of": "Uwaga: GRUB zostanie zainstalowany w MBR dysku",
            "Error": "Błąd",
            
            # Partition operations
            "Remove Partition": "Usuń partycję",
            "Are you sure you want to remove partition": "Czy na pewno chcesz usunąć partycję",
            "This action cannot be undone and all data will be lost!": "Ta operacja jest nieodwracalna, wszystkie dane zostaną utracone!",
            "Cancel": "Anuluj",
            "Format Partition": "Formatuj partycję",
            "Select filesystem type for": "Wybierz system plików dla",
            "Warning: All data will be lost!": "Ostrzeżenie: wszystkie dane zostaną utracone!",
            "ext4": "ext4",
            "Btrfs": "Btrfs",
            "NTFS": "NTFS",
            "FAT32": "FAT32",
            "exFAT": "exFAT",
            "swap": "swap",
            "Unformatted": "Niesformatowane",
            
            # Installation Widget
            "Installing System": "Instalowanie systemu",
            "Preparing installation...": "Przygotowywanie instalacji...",
            "Please wait while the system prepares for installation": "Proszę czekać, system przygotowuje się do instalacji",
            "Step": "Krok",
            "of": "z",
            "Elapsed time": "Czas trwania",
            "Show Details": "Pokaż szczegóły",
            "Hide Details": "Ukryj szczegóły",
            "Cancel Installation?": "Anulować instalację?",
            "Are you sure you want to cancel the installation? This may leave your system in an incomplete state.": "Czy na pewno chcesz anulować instalację? System może pozostać w stanie nieukończonym.",
            "Keep Installing": "Kontynuuj instalację",
            "Cancel Installation": "Anuluj instalację",
            "Cancelling installation...": "Anulowanie instalacji...",
            "Installation Complete!": "Instalacja zakończona!",
            "System installed successfully": "System został pomyślnie zainstalowany",
            "Your system has been installed and is ready to use.": "Twój system został zainstalowany i jest gotowy do użycia.",
            "Finish": "Zakończ",
            "Installation Failed": "Instalacja nie powiodła się",
            "An error occurred during installation": "Wystąpił błąd podczas instalacji",
            "Try Again": "Spróbuj ponownie",
            "Installation Cancelled": "Instalacja anulowana",
            "Installation was cancelled by user": "Instalacja została anulowana przez użytkownika",
            "The installation process was interrupted.": "Proces instalacji został przerwany.",
            "Restart": "Uruchom ponownie",
            "INSTALLATION COMPLETED SUCCESSFULLY!": "INSTALACJA ZAKOŃCZONA SUKCESEM!",
            
            # Installation steps
            "Creating installation directories": "Tworzenie katalogów instalacyjnych",
            "Setting up temporary installation directories": "Konfigurowanie tymczasowych katalogów instalacyjnych",
            "Mounting installation image": "Montowanie obrazu instalacyjnego",
            "containing the system image": "zawierającego obraz systemu",
            "Mounting root partition": "Montowanie partycji root",
            "Mounting the root partition based on /etc/fstab": "Montowanie partycji root zgodnie z /etc/fstab",
            "Creating boot directory": "Tworzenie katalogu boot",
            "Creating boot mount point": "Tworzenie punktu montowania boot",
            "Mounting boot partition": "Montowanie partycji boot",
            "Mounting the boot partition based on /etc/fstab": "Montowanie partycji boot zgodnie z /etc/fstab",
            "Copying system files": "Kopiowanie plików systemowych",
            "Copying the system image to your disk. This may take several minutes...": "Kopiowanie obrazu systemu na dysk. To może potrwać kilka minut...",
            "Verifying file copy": "Sprawdzanie kopiowania plików",
            "Verifying that files were copied successfully": "Sprawdzanie, czy pliki zostały skopiowane pomyślnie",
            "Removing live ISO fstab": "Usuwanie pliku fstab LiveISO",
            "Removing the live ISO filesystem configuration": "Usuwanie konfiguracji systemu plików LiveISO",
            "Applying installer configuration": "Zastosowywanie konfiguracji instalatora",
            "Copying installer configuration files to the new system": "Kopiowanie plików konfiguracyjnych instalatora do nowego systemu",
            "Removing wheel sudo configuration": "Usuwanie konfiguracji sudo dla wheel",
            "Removing temporary sudo configuration": "Usuwanie tymczasowej konfiguracji sudo",
            "Changing system's language": "Zmiana języka systemu",
            "Changing system's language to a selected one": "Zmiana języka systemu na wybrany",
            "Setting up timezone": "Ustawianie strefy czasowej",
            "Linking timezone to the selected one in the installer": "Łączenie strefy czasowej z wybraną w instalatorze",
            "Setting up keyboard layout": "Ustawianie układu klawiatury",
            "Using proper commands in chroot environment to set up keyboard layout": "Używanie odpowiednich poleceń w środowisku chroot do ustawienia układu klawiatury",
            "Adding user": "Dodawanie użytkownika",
            "Adding user, setting it's password and hostname for the PC": "Dodawanie użytkownika, ustawianie hasła i nazwy hosta komputera",
            "Cleaning out rootfs": "Czyszczenie rootfs",
            "Cleaning out rootfs from LiveISO's config and applying post-install scripts": "Czyszczenie rootfs z konfiguracji LiveISO i stosowanie skryptów po instalacji",
            "Installing bootloader": "Instalowanie bootloadera",
            "Checking for other systems installed and installing proper bootloader": "Sprawdzanie innych zainstalowanych systemów i instalowanie odpowiedniego bootloadera",
            "Unmounting filesystems": "Odmontowywanie systemów plików",
            "Safely unmounting all filesystems": "Bezpieczne odmontowywanie wszystkich systemów plików",
            
            # Finish Widget
            "Installation has finished successfully!": "Instalacja zakończyła się pomyślnie!",
            "Everything is set up for you. Thank you for choosing LineXin.": "Wszystko zostało skonfigurowane. Dziękujemy za wybór LineXin.",
            "Reboot the system to finish installation.": "Uruchom ponownie system, aby zakończyć instalację.",
            "Reboot": "Uruchom ponownie",
            "Reboot System": "Uruchom ponownie system",
            "Are you sure you want to reboot now?": "Czy na pewno chcesz teraz uruchomić ponownie?",
            "Reboot Failed": "Ponowne uruchomienie nie powiodło się",
            "Could not reboot the system. Please reboot manually.": "Nie udało się uruchomić ponownie systemu. Zrób to ręcznie.",
            "Installation Complete": "Instalacja zakończona"
        }

    def translate_dialog(self, dialog):
        """Immediately translate a dialog when it's created"""
        try:
            # Translate heading
            heading = dialog.get_heading()
            if heading:
                dialog.set_heading(self.get_text(heading))

            # Translate body with bullet preservation
            body = dialog.get_body()
            if body:
                lines = body.splitlines()
                translated_lines = []
                for line in lines:
                    if not line.strip():
                        translated_lines.append(line)
                        continue
                    
                    # Handle bullet points
                    bullet = ""
                    stripped = line
                    if stripped.lstrip().startswith("• "):
                        bullet = "• "
                        stripped = stripped.lstrip()[2:].strip()
                    else:
                        stripped = stripped.strip()
                    
                    translated = self.get_text(stripped)
                    translated_lines.append(f"{bullet}{translated}")
                
                dialog.set_body("\n".join(translated_lines))
            
            # Translate response labels
            responses = []
            # Unfortunately, GTK4 doesn't provide a direct way to get response labels
            # So we'll handle this when creating dialogs
            
        except Exception as e:
            print(f"Error translating dialog: {e}")


    def register_widget(self, widget):
        """Register a top-level widget for automatic translation updates"""
        if widget not in self.registered_widgets:
            self.registered_widgets.append(widget)
            print(f"Registered widget for translation: {widget.__class__.__name__}")
    
    def set_language(self, language_code):
        """Set the current language and update all registered widgets"""
        if language_code in self.translations:
            old_language = self.current_language
            self.current_language = language_code
            if old_language != language_code:
                print(f"Language changed from {old_language} to {language_code}")
                self.update_all_widgets()
                self.emit('language-changed', language_code)
            return True
        else:
            print(f"Warning: Language {language_code} not available, keeping {self.current_language}")
            return False
    
    def update_all_widgets(self):
        """Update all registered widgets by traversing their widget trees"""
        for widget in self.registered_widgets:
            if widget and not widget.get_destroyed() if hasattr(widget, 'get_destroyed') else True:
                self.update_widget_tree(widget)
    
    def update_widget_tree(self, widget):
        """Recursively update all translatable elements in a widget tree"""
        try:
            # Update current widget if it's translatable
            self.update_widget(widget)
            
            # Recursively update children
            if hasattr(widget, 'get_first_child'):
                # GTK4 style iteration
                child = widget.get_first_child()
                while child:
                    self.update_widget_tree(child)
                    child = child.get_next_sibling()
            elif hasattr(widget, 'get_child'):
                # Single child containers
                child = widget.get_child()
                if child:
                    self.update_widget_tree(child)
            elif hasattr(widget, 'get_children'):
                # GTK3 style (fallback)
                for child in widget.get_children():
                    self.update_widget_tree(child)
                    
                    
        except Exception as e:
            # Silently continue if we can't access a widget
            pass
    
    def update_widget(self, widget):
        """Update a single widget if it contains translatable text"""
        try:
            widget_type = type(widget).__name__
            
            if isinstance(widget, Gtk.Button):
                label = widget.get_label()
                if label and label in self.translations[self.current_language]:
                    widget.set_label(self.translations[self.current_language][label])
                    
            elif isinstance(widget, Gtk.Label):
                # Handle both regular text and markup
                text = widget.get_text()
                if text and text in self.translations[self.current_language]:
                    # Preserve markup structure for titles
                    if 'size="xx-large"' in (widget.get_label() or ""):
                        widget.set_markup(f'<span size="xx-large" weight="bold">{self.translations[self.current_language][text]}</span>')
                    else:
                        widget.set_text(self.translations[self.current_language][text])
                        
            elif isinstance(widget, Gtk.SearchEntry) or isinstance(widget, Gtk.Entry):
                placeholder = widget.get_placeholder_text()
                if placeholder and placeholder in self.translations[self.current_language]:
                    widget.set_placeholder_text(self.translations[self.current_language][placeholder])
                    
            elif isinstance(widget, Adw.WindowTitle):
                title = widget.get_title()
                if title and title in self.translations[self.current_language]:
                    widget.set_title(self.translations[self.current_language][title])

            elif isinstance(widget, Adw.MessageDialog):
                # Heading: simple direct lookup
                heading = widget.get_heading()
                if heading:
                    widget.set_heading(self.get_text(heading))

                # Body: translate known lines, preserve bullets and unknown/dynamic lines
                body = widget.get_body()
                if body:
                    lines = body.splitlines()
                    out = []
                    for line in lines:
                        # Keep empty spacer lines
                        if not line.strip():
                            out.append(line)
                            continue

                        # Preserve bullet prefix if present
                        bullet = ""
                        stripped = line
                        if stripped.lstrip().startswith("• "):
                            # normalize: keep exact leading "• " if present
                            # (works even if line had leading spaces)
                            bullet = "• "
                            stripped = stripped.lstrip()[2:].strip()
                        else:
                            stripped = stripped.strip()

                        # translate whole-line phrase if we have it, else keep as-is
                        translated = self.get_text(stripped)
                        out.append(f"{bullet}{translated}")
                    widget.set_body("\n".join(out))       
                    
        except Exception as e:
            # Silently continue if we can't update a specific widget
            pass
    
    def get_text(self, key):
        """Get translated text for the current language with fallback to English"""
        if self.current_language in self.translations:
            if key in self.translations[self.current_language]:
                return self.translations[self.current_language][key]
        
        # Fallback to English
        if key in self.translations["en_US.UTF-8"]:
            return self.translations["en_US.UTF-8"][key]
        
        # Last resort: return the key itself
        return key
    
    def get_current_language(self):
        """Get the current language code"""
        return self.current_language

# Singleton access
def get_localization_manager():
    """Get the singleton SimpleLocalizationManager instance"""
    return SimpleLocalizationManager()

# Convenience function for getting translated text (optional)
def _(key):
    """Get translated text using the localization manager"""
    return get_localization_manager().get_text(key)