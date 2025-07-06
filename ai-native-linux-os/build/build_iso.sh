#!/bin/bash

# AI-Native Linux OS ISO Build Script

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
ISO_DIR="${BUILD_DIR}/iso"
MOUNT_DIR="${BUILD_DIR}/mount"
BASE_ISO_URL="https://cdimage.ubuntu.com/ubuntu-base/releases/22.04/release/ubuntu-base-22.04-base-amd64.tar.gz"
OUTPUT_ISO="ai-native-linux-os.iso"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

check_dependencies() {
    log "Checking dependencies..."
    
    local deps=("debootstrap" "squashfs-tools" "xorriso" "isolinux" "syslinux-utils")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            error "Required dependency '$dep' is not installed"
        fi
    done
    
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root"
    fi
}

setup_directories() {
    log "Setting up build directories..."
    
    mkdir -p "$BUILD_DIR"
    mkdir -p "$ISO_DIR"
    mkdir -p "$MOUNT_DIR"
    
    # Clean previous build
    if [ -d "$ISO_DIR/live" ]; then
        rm -rf "$ISO_DIR/live"
    fi
    
    mkdir -p "$ISO_DIR/live"
    mkdir -p "$ISO_DIR/isolinux"
}

create_base_system() {
    log "Creating base Ubuntu system..."
    
    # Use debootstrap to create minimal Ubuntu system
    debootstrap --arch=amd64 --variant=minbase jammy "$MOUNT_DIR" http://archive.ubuntu.com/ubuntu/
    
    # Mount necessary filesystems
    mount --bind /proc "$MOUNT_DIR/proc"
    mount --bind /sys "$MOUNT_DIR/sys"
    mount --bind /dev "$MOUNT_DIR/dev"
    mount --bind /dev/pts "$MOUNT_DIR/dev/pts"
}

configure_base_system() {
    log "Configuring base system..."
    
    # Configure APT sources
    cat > "$MOUNT_DIR/etc/apt/sources.list" << EOF
deb http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
EOF
    
    # Configure hostname
    echo "ai-native-linux" > "$MOUNT_DIR/etc/hostname"
    
    # Configure hosts
    cat > "$MOUNT_DIR/etc/hosts" << EOF
127.0.0.1   localhost
127.0.1.1   ai-native-linux
::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF
    
    # Install essential packages
    chroot "$MOUNT_DIR" apt-get update
    chroot "$MOUNT_DIR" apt-get install -y \
        linux-generic \
        casper \
        lupin-casper \
        discover \
        laptop-detect \
        os-prober \
        network-manager \
        resolvconf \
        net-tools \
        wireless-tools \
        wpagui \
        locales \
        linux-headers-generic \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        systemd \
        systemd-sysv \
        sudo \
        openssh-server \
        curl \
        wget \
        vim \
        htop \
        git
    
    # Configure locale
    chroot "$MOUNT_DIR" locale-gen en_US.UTF-8
    
    # Configure user
    chroot "$MOUNT_DIR" useradd -m -s /bin/bash -G sudo ai-user
    chroot "$MOUNT_DIR" passwd -d ai-user
    
    # Enable auto-login
    mkdir -p "$MOUNT_DIR/etc/systemd/system/getty@tty1.service.d"
    cat > "$MOUNT_DIR/etc/systemd/system/getty@tty1.service.d/autologin.conf" << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ai-user --noclear %I \$TERM
EOF
}

install_ai_components() {
    log "Installing AI-Native Linux components..."
    
    # Copy source files
    mkdir -p "$MOUNT_DIR/opt/ai-native-linux"
    cp -r "$PROJECT_ROOT/src" "$MOUNT_DIR/opt/ai-native-linux/"
    cp "$PROJECT_ROOT/requirements.txt" "$MOUNT_DIR/opt/ai-native-linux/"
    
    # Install Python dependencies
    chroot "$MOUNT_DIR" pip3 install -r /opt/ai-native-linux/requirements.txt
    
    # Create systemd services
    create_systemd_services
    
    # Create shell aliases and functions
    create_shell_integration
    
    # Make scripts executable
    chmod +x "$MOUNT_DIR/opt/ai-native-linux/src/ai_shell/ai_shell.py"
    chmod +x "$MOUNT_DIR/opt/ai-native-linux/src/quest_log/quest_log_daemon.py"
    chmod +x "$MOUNT_DIR/opt/ai-native-linux/src/quest_log/quest_log_cli.py"
    chmod +x "$MOUNT_DIR/opt/ai-native-linux/src/kernel_monitor/kernel_monitor.py"
    chmod +x "$MOUNT_DIR/opt/ai-native-linux/src/self_healing/self_healing_service.py"
    
    # Create symlinks in /usr/local/bin
    ln -sf "/opt/ai-native-linux/src/ai_shell/ai_shell.py" "$MOUNT_DIR/usr/local/bin/ai"
    ln -sf "/opt/ai-native-linux/src/quest_log/quest_log_cli.py" "$MOUNT_DIR/usr/local/bin/quest"
    
    # Enable services
    chroot "$MOUNT_DIR" systemctl enable quest-log-daemon
    chroot "$MOUNT_DIR" systemctl enable kernel-monitor
    chroot "$MOUNT_DIR" systemctl enable self-healing-service
}

create_systemd_services() {
    log "Creating systemd services..."
    
    # Quest Log Daemon
    cat > "$MOUNT_DIR/etc/systemd/system/quest-log-daemon.service" << EOF
[Unit]
Description=Quest Log Daemon
After=network.target
Wants=network.target

[Service]
Type=simple
User=ai-user
ExecStart=/usr/bin/python3 /opt/ai-native-linux/src/quest_log/quest_log_daemon.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Kernel Monitor
    cat > "$MOUNT_DIR/etc/systemd/system/kernel-monitor.service" << EOF
[Unit]
Description=AI Kernel Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=ai-user
ExecStart=/usr/bin/python3 /opt/ai-native-linux/src/kernel_monitor/kernel_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Self-Healing Service
    cat > "$MOUNT_DIR/etc/systemd/system/self-healing-service.service" << EOF
[Unit]
Description=Self-Healing Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/ai-native-linux/src/self_healing/self_healing_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
}

create_shell_integration() {
    log "Creating shell integration..."
    
    # Add to .bashrc
    cat >> "$MOUNT_DIR/home/ai-user/.bashrc" << 'EOF'

# AI-Native Linux OS Integration
export PATH="/opt/ai-native-linux/src:$PATH"

# AI Shell Assistant alias
alias ai='python3 /opt/ai-native-linux/src/ai_shell/ai_shell.py'

# Quest Log aliases
alias quest='python3 /opt/ai-native-linux/src/quest_log/quest_log_cli.py'
alias qlog='quest commands --limit 10'
alias qsearch='quest search'

# Welcome message
echo "Welcome to AI-Native Linux OS!"
echo "Available commands:"
echo "  ai <query>     - AI Shell Assistant"
echo "  quest          - Quest Log viewer"
echo "  qlog           - Recent commands"
echo "  qsearch <term> - Search logs"
echo ""
EOF
    
    # Set ownership
    chroot "$MOUNT_DIR" chown ai-user:ai-user /home/ai-user/.bashrc
}

create_squashfs() {
    log "Creating SquashFS filesystem..."
    
    # Unmount filesystems
    umount "$MOUNT_DIR/proc" || true
    umount "$MOUNT_DIR/sys" || true
    umount "$MOUNT_DIR/dev/pts" || true
    umount "$MOUNT_DIR/dev" || true
    
    # Clean up
    chroot "$MOUNT_DIR" apt-get clean
    rm -rf "$MOUNT_DIR/var/cache/apt/archives/*.deb"
    rm -rf "$MOUNT_DIR/var/lib/apt/lists/*"
    rm -rf "$MOUNT_DIR/tmp/*"
    
    # Create squashfs
    mksquashfs "$MOUNT_DIR" "$ISO_DIR/live/filesystem.squashfs" -comp xz
    
    # Create filesystem.size
    du -sx --block-size=1 "$MOUNT_DIR" | cut -f1 > "$ISO_DIR/live/filesystem.size"
}

create_iso_structure() {
    log "Creating ISO structure..."
    
    # Copy isolinux files
    cp /usr/lib/ISOLINUX/isolinux.bin "$ISO_DIR/isolinux/"
    cp /usr/lib/syslinux/modules/bios/* "$ISO_DIR/isolinux/"
    
    # Create isolinux.cfg
    cat > "$ISO_DIR/isolinux/isolinux.cfg" << EOF
DEFAULT live
LABEL live
  MENU LABEL ^Start AI-Native Linux OS
  KERNEL /casper/vmlinuz
  APPEND initrd=/casper/initrd boot=casper quiet splash ---
LABEL check
  MENU LABEL ^Check disc for defects
  KERNEL /casper/vmlinuz
  APPEND initrd=/casper/initrd boot=casper integrity-check quiet splash ---
DISPLAY isolinux.txt
TIMEOUT 300
PROMPT 0
EOF
    
    # Create isolinux.txt
    cat > "$ISO_DIR/isolinux/isolinux.txt" << EOF
AI-Native Linux OS

Boot options:
- Start AI-Native Linux OS
- Check disc for defects

Press ENTER to boot automatically in 30 seconds.
EOF
    
    # Copy kernel and initrd
    mkdir -p "$ISO_DIR/casper"
    cp "$MOUNT_DIR/boot/vmlinuz-"* "$ISO_DIR/casper/vmlinuz"
    cp "$MOUNT_DIR/boot/initrd.img-"* "$ISO_DIR/casper/initrd"
    
    # Create manifest
    chroot "$MOUNT_DIR" dpkg-query -W --showformat='${Package} ${Version}\n' > "$ISO_DIR/casper/filesystem.manifest"
    cp "$ISO_DIR/casper/filesystem.manifest" "$ISO_DIR/casper/filesystem.manifest-desktop"
}

build_iso() {
    log "Building ISO image..."
    
    # Generate MD5 checksums
    cd "$ISO_DIR"
    find . -type f -print0 | xargs -0 md5sum | grep -v "\./md5sum.txt" > md5sum.txt
    
    # Build ISO
    xorriso -as mkisofs \
        -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
        -c isolinux/boot.cat \
        -b isolinux/isolinux.bin \
        -no-emul-boot \
        -boot-load-size 4 \
        -boot-info-table \
        -eltorito-alt-boot \
        -e boot/grub/efi.img \
        -no-emul-boot \
        -isohybrid-gpt-basdat \
        -V "AI-Native Linux OS" \
        -o "$BUILD_DIR/$OUTPUT_ISO" \
        "$ISO_DIR"
    
    log "ISO created: $BUILD_DIR/$OUTPUT_ISO"
}

cleanup() {
    log "Cleaning up..."
    
    # Unmount any remaining filesystems
    umount "$MOUNT_DIR/proc" 2>/dev/null || true
    umount "$MOUNT_DIR/sys" 2>/dev/null || true
    umount "$MOUNT_DIR/dev/pts" 2>/dev/null || true
    umount "$MOUNT_DIR/dev" 2>/dev/null || true
    
    # Remove build directories if requested
    if [ "$1" = "--clean" ]; then
        rm -rf "$ISO_DIR"
        rm -rf "$MOUNT_DIR"
    fi
}

main() {
    log "Starting AI-Native Linux OS build process..."
    
    check_dependencies
    setup_directories
    create_base_system
    configure_base_system
    install_ai_components
    create_squashfs
    create_iso_structure
    build_iso
    cleanup
    
    log "Build completed successfully!"
    log "ISO file: $BUILD_DIR/$OUTPUT_ISO"
    log "Size: $(du -h "$BUILD_DIR/$OUTPUT_ISO" | cut -f1)"
}

# Handle script arguments
case "$1" in
    --clean)
        cleanup --clean
        ;;
    *)
        main "$@"
        ;;
esac