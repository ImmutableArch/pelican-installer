#!/bin/bash

# Bootloader Configuration Script for Arch Linux
# This script detects the system configuration and installs the appropriate bootloader
# NOTE: This script should be run from within arch-chroot

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_msg() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

# Detect ESP mount point
detect_esp() {
    # Check common ESP mount points
    for esp_path in "/boot/efi" "/boot" "/efi"; do
        if mountpoint -q "$esp_path" 2>/dev/null; then
            # Verify it's actually an ESP by checking for EFI directory or FAT filesystem
            if [ -d "$esp_path/EFI" ] || [ -w "$esp_path" ]; then
                echo "$esp_path"
                return 0
            fi
        fi
    done
    
    # Fallback: look for FAT32 partitions that might be ESP
    local esp_part=$(lsblk -f | grep -E "(fat32|vfat)" | head -1 | awk '{print $1}')
    if [ -n "$esp_part" ]; then
        # Default to /boot if ESP partition exists but not mounted properly
        echo "/boot"
        return 0
    fi
    
    return 1
}

# Detect boot mode (UEFI or Legacy)
detect_boot_mode() {
    if [ -d /sys/firmware/efi/efivars ]; then
        echo "uefi"
    else
        echo "legacy"
    fi
}

# Detect other operating systems with improved detection
detect_other_os() {
    local other_os_found=false
    
    # Redirect all diagnostic output to stderr so it doesn't interfere with return value
    print_msg "Detecting other operating systems..." >&2
    
    # Method 1: Check ESP for Windows Boot Manager (most reliable)
    if [ "$BOOT_MODE" = "uefi" ] && [ -n "$ESP_PATH" ]; then
        if [ -d "$ESP_PATH/EFI/Microsoft" ]; then
            print_msg "Windows UEFI installation detected via ESP" >&2
            other_os_found=true
        fi
        
        # Check for other Linux distros in ESP (exclude common system directories)
        if [ -d "$ESP_PATH/EFI" ]; then
            for dir in "$ESP_PATH/EFI"/*; do
                if [ -d "$dir" ]; then
                    local dirname=$(basename "$dir")
                    case "$dirname" in
                        ubuntu|debian|fedora|opensuse|manjaro|pop|elementary|mint|centos|rhel)
                            print_msg "Linux distribution detected: $dirname" >&2
                            other_os_found=true
                            ;;
                        # Ignore system directories and current installation
                        BOOT|Boot|systemd|Linexin|tools|*)
                            ;;
                    esac
                fi
            done
        fi
    fi
    
    # Method 2: Check for NTFS partitions with actual Windows installation
    if [ "$other_os_found" = "false" ]; then
        local ntfs_parts=$(lsblk -no NAME,FSTYPE | grep -w ntfs | awk '{print $1}')
        if [ -n "$ntfs_parts" ]; then
            print_msg "NTFS partition(s) detected, verifying Windows installation..." >&2
            for part in $ntfs_parts; do
                local temp_mount="/tmp/os_check_$"
                mkdir -p "$temp_mount" 2>/dev/null
                if mount -t ntfs-3g -o ro "/dev/$part" "$temp_mount" 2>/dev/null; then
                    # Check for actual Windows system directories (not just any NTFS partition)
                    if [ -d "$temp_mount/Windows/System32" ] || \
                       [ -d "$temp_mount/windows/system32" ] || \
                       [ -f "$temp_mount/bootmgr" ] && [ -d "$temp_mount/Windows" ]; then
                        print_msg "Windows installation confirmed on /dev/$part" >&2
                        other_os_found=true
                    else
                        print_msg "NTFS partition /dev/$part does not contain Windows" >&2
                    fi
                    umount "$temp_mount" 2>/dev/null
                else
                    print_msg "Could not mount NTFS partition /dev/$part for verification" >&2
                fi
                rmdir "$temp_mount" 2>/dev/null
                
                # Break early if Windows found
                if [ "$other_os_found" = "true" ]; then
                    break
                fi
            done
        fi
    fi
    
    # Method 3: Check EFI boot entries (only if no other OS found yet)
    if [ "$other_os_found" = "false" ] && [ "$BOOT_MODE" = "uefi" ] && command -v efibootmgr &> /dev/null; then
        local efi_entries=$(efibootmgr 2>/dev/null | grep -v "BootOrder\|BootCurrent\|Timeout\|BootNext")
        if echo "$efi_entries" | grep -qi "windows\|microsoft"; then
            print_msg "Windows detected via EFI boot entries" >&2
            other_os_found=true
        elif echo "$efi_entries" | grep -qi "ubuntu\|debian\|fedora\|opensuse\|centos\|rhel"; then
            print_msg "Other Linux distribution detected via EFI boot entries" >&2
            other_os_found=true
        fi
    fi
    
    # Method 4: Use os-prober as final verification (only if suspicious findings)
    if [ "$other_os_found" = "true" ]; then
        if ! command -v os-prober &> /dev/null; then
            print_msg "Installing os-prober for verification..." >&2
            pacman -S --noconfirm os-prober ntfs-3g >&2 2>/dev/null || true
        fi
        
        # Run os-prober with timeout to verify findings
        local os_prober_output=""
        if command -v os-prober &> /dev/null; then
            if command -v timeout &> /dev/null; then
                os_prober_output=$(timeout 30 os-prober 2>/dev/null || echo "")
            else
                os_prober_output=$(os-prober 2>/dev/null || echo "")
            fi
            
            if [ -n "$os_prober_output" ]; then
                print_msg "os-prober found: $(echo "$os_prober_output" | wc -l) other OS(es)" >&2
            else
                print_msg "os-prober found no other operating systems" >&2
                # If os-prober finds nothing, be more conservative
                other_os_found=false
            fi
        fi
    fi
    
    # Method 5: Check for other Linux installations (more conservative)
    if [ "$other_os_found" = "false" ]; then
        local current_root_uuid=$(findmnt -no UUID /)
        local other_linux_found=false
        
        for part in $(lsblk -no UUID,FSTYPE | grep -E "ext4|btrfs|xfs" | awk '{print $1}'); do
            if [ -n "$part" ] && [ "$part" != "$current_root_uuid" ]; then
                local temp_mount="/tmp/os_check_$"
                mkdir -p "$temp_mount" 2>/dev/null
                if mount UUID="$part" "$temp_mount" 2>/dev/null; then
                    # More specific checks for actual Linux installations
                    if [ -f "$temp_mount/etc/os-release" ] && [ -d "$temp_mount/boot" ] && \
                       [ -f "$temp_mount/boot/vmlinuz"* ] && [ "$temp_mount" != "/" ]; then
                        local os_name=$(grep '^NAME=' "$temp_mount/etc/os-release" 2>/dev/null | cut -d'"' -f2)
                        if [ -n "$os_name" ] && [ "$os_name" != "Linexin" ]; then
                            print_msg "Additional Linux installation detected: $os_name" >&2
                            other_linux_found=true
                        fi
                    fi
                    umount "$temp_mount" 2>/dev/null
                fi
                rmdir "$temp_mount" 2>/dev/null
            fi
        done
        
        other_os_found=$other_linux_found
    fi
    
    # Return only the clean value
    echo "$other_os_found"
}

# Install and configure systemd-boot
install_systemd_boot() {
    local esp_path=$1
    print_msg "Installing systemd-boot with ESP at $esp_path..."
    
    # Install systemd-boot
    if ! bootctl --esp-path="$esp_path" install; then
        print_error "bootctl install failed"
        exit 1
    fi
    
    # Create loader configuration
    mkdir -p "$esp_path/loader"
    cat > "$esp_path/loader/loader.conf" <<EOF
default  linexin.conf
timeout  0
console-mode max
editor   no
EOF
    
    # Create boot entry
    mkdir -p "$esp_path/loader/entries"
    local root_uuid=$(findmnt -no UUID /)
    cat > "$esp_path/loader/entries/linexin.conf" <<EOF
title   Linexin
linux   /vmlinuz-linux
initrd  /initramfs-linux.img
options root=UUID=$root_uuid rw quiet splash
EOF
    
    # Create fallback entry
    cat > "$esp_path/loader/entries/arch-fallback.conf" <<EOF
title   Linexin (fallback initramfs)
linux   /vmlinuz-linux
initrd  /initramfs-linux-fallback.img
options root=UUID=$root_uuid rw
EOF
    
    # Set up EFI boot entry safely
    local esp_device=$(findmnt -no SOURCE "$esp_path")
    if [ -n "$esp_device" ]; then
        local esp_part_num=$(echo "$esp_device" | grep -o '[0-9]*$')
        local esp_disk=$(echo "$esp_device" | sed 's/[0-9]*$//')
        
        if [ -n "$esp_part_num" ] && [ -n "$esp_disk" ]; then
            if efibootmgr -c -d "$esp_disk" -p "$esp_part_num" -L "Linexin QuickBoot" -l "\\EFI\\systemd\\systemd-bootx64.efi" 2>/dev/null; then
                local linux_boot=$(efibootmgr | grep "Linexin QuickBoot" | grep -o '^Boot[0-9A-F]\{4\}' | sed 's/Boot//' | head -1)
                if [ -n "$linux_boot" ]; then
                    local other_boots=$(efibootmgr | grep "BootOrder:" | cut -d: -f2 | tr -d ' ' | sed "s/$linux_boot,\?//g" | sed 's/,$//')
                    efibootmgr -o "$linux_boot,$other_boots" 2>/dev/null || true
                fi
            fi
        fi
    fi
    
    print_msg "systemd-boot installed and configured successfully"
}

# Install and configure GRUB
install_grub() {
    local boot_mode=$1
    local esp_path=$2
    print_msg "Installing GRUB for $boot_mode..."
    
    # Install required packages
    if [ "$boot_mode" = "uefi" ]; then
        pacman -S --noconfirm grub efibootmgr os-prober ntfs-3g
        
        # Install GRUB for UEFI with Linexin branding
        if ! grub-install --target=x86_64-efi --efi-directory="$esp_path" --bootloader-id=Linexin; then
            print_error "GRUB UEFI installation failed"
            exit 1
        fi
    else
        pacman -S --noconfirm grub os-prober ntfs-3g
        
        # Detect the disk where root is installed
        local root_device=$(findmnt -no SOURCE /)
        local root_disk="/dev/$(lsblk -no PKNAME "$root_device" | head -1)"
        
        print_msg "Installing GRUB to $root_disk"
        if ! grub-install --target=i386-pc "$root_disk"; then
            print_error "GRUB Legacy installation failed"
            exit 1
        fi
    fi
    
    # Customize GRUB configuration
    print_msg "Customizing GRUB configuration..."
    
    # Backup original GRUB config if it exists
    if [ -f /etc/default/grub ]; then
        cp /etc/default/grub /etc/default/grub.bak
    fi
    
    # Create custom GRUB configuration
    cat > /etc/default/grub <<'EOF'
# GRUB Configuration for Linexin
GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_DISTRIBUTOR="Linexin"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_CMDLINE_LINUX=""

# Display settings
GRUB_TERMINAL_INPUT=console
GRUB_GFXMODE=auto
GRUB_GFXPAYLOAD_LINUX=keep
GRUB_DISABLE_RECOVERY=false

# OS Prober for dual-boot
GRUB_DISABLE_OS_PROBER=false

# Theme and appearance
GRUB_COLOR_NORMAL="light-blue/black"
GRUB_COLOR_HIGHLIGHT="light-cyan/blue"
EOF
    
    # Modify lsb-release if it exists
    if [ -f /etc/lsb-release ]; then
        cp /etc/lsb-release /etc/lsb-release.bak
        sed -i 's/DISTRIB_ID=.*/DISTRIB_ID=Linexin/' /etc/lsb-release
        sed -i 's/DISTRIB_DESCRIPTION=.*/DISTRIB_DESCRIPTION="Linexin"/' /etc/lsb-release
    else
        # Create lsb-release for Linexin
        cat > /etc/lsb-release <<'EOLSB'
DISTRIB_ID=Linexin
DISTRIB_RELEASE=rolling
DISTRIB_DESCRIPTION="Linexin"
EOLSB
    fi
    
    # Generate GRUB configuration
    print_msg "Generating GRUB configuration..."
    if ! grub-mkconfig -o /boot/grub/grub.cfg; then
        print_error "GRUB configuration generation failed"
        exit 1
    fi
    
    # Post-process grub.cfg to ensure Linexin naming
    if [ -f /boot/grub/grub.cfg ]; then
        sed -i 's/Arch Linux/Linexin/g' /boot/grub/grub.cfg
        sed -i 's/menuentry '\''Arch'\''/menuentry '\''Linexin'\''/g' /boot/grub/grub.cfg
        sed -i "s/menuentry \"Arch/menuentry \"Linexin/g" /boot/grub/grub.cfg
    fi
    
    print_msg "GRUB installed and configured successfully with Linexin branding"
}

# Install and configure rEFInd
install_refind() {
    local esp_path=$1
    print_msg "Installing rEFInd with ESP at $esp_path..."
    
    # Install rEFInd package
    if ! pacman -S --noconfirm refind; then
        print_error "Failed to install rEFInd package"
        exit 1
    fi
    
    # Manual rEFInd installation for arch-chroot environment
    print_msg "Installing rEFInd files..."
    
    # Create necessary directories
    mkdir -p "$esp_path/EFI/refind" || {
        print_error "Failed to create rEFInd directory"
        exit 1
    }
    mkdir -p "$esp_path/EFI/BOOT"
    
    # Copy rEFInd files
    if [ -d /usr/share/refind ]; then
        cp -r /usr/share/refind/* "$esp_path/EFI/refind/" || {
            print_error "Failed to copy rEFInd files"
            exit 1
        }
    else
        print_error "rEFInd files not found in /usr/share/refind"
        exit 1
    fi
    
    # Copy the EFI binary as fallback bootloader
    if [ -f "$esp_path/EFI/refind/refind_x64.efi" ]; then
        cp "$esp_path/EFI/refind/refind_x64.efi" "$esp_path/EFI/BOOT/bootx64.efi" 2>/dev/null || true
    fi
    
    # Create refind_linux.conf for kernel parameters
    local root_uuid=$(findmnt -no UUID /)
    cat > "$esp_path/refind_linux.conf" <<EOF
"Boot Linexin"                 "root=UUID=$root_uuid rw quiet splash"
"Boot Linexin (terminal)"      "root=UUID=$root_uuid rw systemd.unit=multi-user.target"
"Boot to single-user mode"     "root=UUID=$root_uuid rw single"
EOF
    
    # Create a basic refind.conf
    cat > "$esp_path/EFI/refind/refind.conf" <<'EOF'
# rEFInd configuration for Linexin

# Timeout in seconds
timeout 5

# Hide user interface elements
hideui singleuser,hints,arrows,badges,hidden_tags, label

# Icon size
big_icon_size 128
small_icon_size 48

# Default selection
default_selection "vmlinuz-linux"

# Scan for kernels
scan_all_linux_kernels true
fold_linux_kernels true

# Include Windows loaders
windows_recovery_files LRS_ESP:/EFI/Microsoft/Boot/bootmgfw.efi

# Scan options - UEFI only, no legacy BIOS scanning
scanfor manual,internal,external,optical

# Don't scan these directories
dont_scan_dirs ESP:/EFI/boot,ESP:/EFI/Boot

# Extra kernel parameters
extra_kernel_version_strings linux-lts,linux

# Load rEFInd theme Regular
include themes/refind-theme-regular/theme.conf
EOF
    
    # Register rEFInd with EFI safely
    print_msg "Registering rEFInd with EFI..."
    local esp_device=$(findmnt -no SOURCE "$esp_path" 2>/dev/null)
    
    if [ -z "$esp_device" ]; then
        print_warning "Could not determine ESP device, skipping EFI registration"
        print_msg "rEFInd installed successfully (manual EFI entry creation may be needed)"
        return 0
    fi
    
    local esp_part_num=$(echo "$esp_device" | grep -o '[0-9]*$')
    local esp_disk=$(echo "$esp_device" | sed 's/[0-9]*$//')
    
    if [ -z "$esp_part_num" ] || [ -z "$esp_disk" ]; then
        print_warning "Could not parse ESP device information, skipping EFI registration"
        print_msg "rEFInd installed successfully (manual EFI entry creation may be needed)"
        return 0
    fi
    
    # Check if efibootmgr is working
    if ! efibootmgr -v >/dev/null 2>&1; then
        print_warning "EFI variables not accessible, skipping EFI boot entry creation"
        print_msg "rEFInd installed successfully (will work as fallback bootloader)"
        return 0
    fi
    
    # Remove any existing rEFInd entries to prevent conflicts
    efibootmgr 2>/dev/null | grep -i refind | grep -o '^Boot[0-9A-F]\{4\}' | sed 's/Boot//' | while read bootnum; do
        efibootmgr -b "$bootnum" -B 2>/dev/null || true
    done
    
    # Create new rEFInd entry with error handling
    if efibootmgr -c -d "$esp_disk" -p "$esp_part_num" -L "rEFInd Boot Manager" -l "\\EFI\\refind\\refind_x64.efi" 2>/dev/null; then
        print_msg "rEFInd EFI entry created successfully"
        
        # Set boot order to prioritize rEFInd
        local refind_boot=$(efibootmgr 2>/dev/null | grep -E "rEFInd|Linexin" | grep -o '^Boot[0-9A-F]\{4\}' | sed 's/Boot//' | head -1)
        if [ -n "$refind_boot" ]; then
            local current_order=$(efibootmgr 2>/dev/null | grep "BootOrder:" | cut -d: -f2 | tr -d ' ')
            local other_boots=$(echo "$current_order" | sed "s/$refind_boot,\?//g" | sed 's/,$//')
            efibootmgr -o "$refind_boot${other_boots:+,$other_boots}" 2>/dev/null || true
        fi
    else
        print_warning "Failed to create EFI boot entry, but rEFInd is installed and will work as fallback"
    fi
    
    print_msg "rEFInd installed and configured successfully"
}

# Main script execution
main() {
    print_msg "Starting bootloader configuration..."

    # Ensure we're in a proper Arch environment
    if [ ! -f /etc/arch-release ]; then
        print_warning "This doesn't appear to be an Arch Linux environment"
    fi

    # Ensure initramfs exists before configuring bootloader
    if [ ! -f "/boot/initramfs-linux.img" ]; then
        print_warning "initramfs not found, generating it first..."
        mkinitcpio -P
    fi

    # Detect system configuration
    local boot_mode
    boot_mode=$(detect_boot_mode)
    print_msg "Boot mode: $boot_mode"

    # Detect ESP for UEFI systems
    local esp_path=""
    if [ "$boot_mode" = "uefi" ]; then
        esp_path=$(detect_esp)
        if [ $? -ne 0 ] || [ -z "$esp_path" ]; then
            print_error "Could not detect ESP mount point for UEFI system"
            print_error "Please ensure your ESP is mounted at /boot, /boot/efi, or /efi"
            exit 1
        fi
        print_msg "ESP detected at: $esp_path"
    fi

    # Set global variables for detect_other_os function
    BOOT_MODE="$boot_mode"
    ESP_PATH="$esp_path"

    # Detect other operating systems
    local other_os
    other_os=$(detect_other_os)

    # Debug output to verify detection
    if [ "$other_os" = "true" ]; then
        print_msg "Multi-boot system confirmed (other OS detected)"
    else
        print_msg "Single OS system (no other OS detected)"
    fi

    # Decision matrix for bootloader selection
    if [ "$other_os" = "true" ]; then
        # Other OS found
        if [ "$boot_mode" = "uefi" ]; then
            # UEFI with other OS - use rEFInd for best multi-boot experience
            print_msg "Multi-boot UEFI system detected - installing rEFInd"
            install_refind "$esp_path"
        else
            # Legacy with other OS - use GRUB (only option for Legacy multi-boot)
            print_msg "Multi-boot Legacy system detected - installing GRUB"
            install_grub "$boot_mode" "$esp_path"
        fi
    else
        # No other OS found
        if [ "$boot_mode" = "uefi" ]; then
            # UEFI without other OS - use systemd-boot (simpler and faster)
            print_msg "Single OS UEFI system detected - installing systemd-boot"
            install_systemd_boot "$esp_path"
        else
            # Legacy without other OS - use GRUB (only option for Legacy)
            print_msg "Single OS Legacy system detected - installing GRUB"
            install_grub "$boot_mode" "$esp_path"
        fi
    fi

    print_msg "Bootloader configuration completed successfully!"
    print_msg "Please reboot and verify that the bootloader appears correctly."
}

# Execute main function
main "$@"
