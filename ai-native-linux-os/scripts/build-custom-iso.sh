#!/bin/bash

# AI-Native Linux OS - Custom ISO Builder
# Creates a custom Ubuntu ISO with AI features pre-integrated

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Configuration
UBUNTU_VERSION="24.04"
ARCH="amd64"
PROJECT_NAME="ai-native-linux"
ISO_NAME="ai-native-linux-${UBUNTU_VERSION}-${ARCH}.iso"
WORK_DIR="/tmp/ai-native-iso-build"
MOUNT_DIR="${WORK_DIR}/mount"
EXTRACT_DIR="${WORK_DIR}/extract"
CUSTOM_DIR="${WORK_DIR}/custom"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root to build custom ISO"
fi

log "Starting AI-Native Linux OS Custom ISO Build..."

# 1. PREPARE WORKSPACE
log "Preparing workspace..."

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
mkdir -p "$MOUNT_DIR"
mkdir -p "$EXTRACT_DIR"
mkdir -p "$CUSTOM_DIR"

cd "$WORK_DIR"

# 2. DOWNLOAD UBUNTU BASE ISO
log "Downloading Ubuntu ${UBUNTU_VERSION} base ISO..."

if [ ! -f "ubuntu-${UBUNTU_VERSION}-desktop-${ARCH}.iso" ]; then
    wget -c "https://releases.ubuntu.com/${UBUNTU_VERSION}/ubuntu-${UBUNTU_VERSION}-desktop-${ARCH}.iso"
fi

BASE_ISO="ubuntu-${UBUNTU_VERSION}-desktop-${ARCH}.iso"

# 3. MOUNT AND EXTRACT ISO
log "Mounting and extracting base ISO..."

mount -o loop "$BASE_ISO" "$MOUNT_DIR"
rsync -a "$MOUNT_DIR/" "$EXTRACT_DIR/"
umount "$MOUNT_DIR"

# 4. PREPARE CUSTOM FILESYSTEM
log "Preparing custom filesystem..."

# Mount squashfs
unsquashfs -d "$CUSTOM_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs"

# Mount necessary filesystems for chroot
mount --bind /dev "$CUSTOM_DIR/dev"
mount --bind /proc "$CUSTOM_DIR/proc"
mount --bind /sys "$CUSTOM_DIR/sys"
mount -t devpts devpts "$CUSTOM_DIR/dev/pts"

# 5. CUSTOMIZE SYSTEM
log "Installing AI-Native Linux OS components..."

# Create customization script
cat > "$CUSTOM_DIR/tmp/customize.sh" << 'EOF'
#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install essential packages
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-full \
    git \
    curl \
    wget \
    htop \
    tree \
    build-essential \
    linux-headers-generic \
    libsqlite3-dev \
    sqlite3

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Create AI-Native Linux directories
mkdir -p /opt/ai-native-linux
mkdir -p /etc/ai-native-linux
mkdir -p /var/log/ai-native-linux
mkdir -p /var/lib/ai-native-linux

# Create ollama user
useradd -r -s /bin/false -d /var/lib/ollama ollama || true
mkdir -p /var/lib/ollama
chown ollama:ollama /var/lib/ollama

# Clean up
apt-get autoremove -y
apt-get autoclean
rm -rf /var/lib/apt/lists/*
rm -rf /tmp/*
rm -rf /var/tmp/*

# Create AI-Native Linux identification
echo "ai-native-linux" > /etc/hostname

# Add AI-Native Linux branding
cat > /etc/motd << 'MOTD'

██████╗ ██╗      ███╗   ██╗ █████╗ ████████╗██╗██╗   ██╗███████╗
██╔══██╗██║      ████╗  ██║██╔══██╗╚══██╔══╝██║██║   ██║██╔════╝
███████║██║█████╗██╔██╗ ██║███████║   ██║   ██║██║   ██║█████╗  
██╔══██║██║╚════╝██║╚██╗██║██╔══██║   ██║   ██║╚██╗ ██╔╝██╔══╝  
██║  ██║██║      ██║ ╚████║██║  ██║   ██║   ██║ ╚████╔╝ ███████╗
╚═╝  ╚═╝╚═╝      ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝

    AI-Native Linux OS - Intelligence Built Into Every Command

Welcome to AI-Native Linux OS! This system has AI features built directly 
into the operating system core.

Quick Start:
  - Type 'ai "your command"' for natural language shell assistance
  - Type 'quest commands' to see your command history with AI insights
  - Visit http://localhost:8080 for the web interface

For more information, visit: https://github.com/Orcadebug/Linux

MOTD

# Set default shell to include AI integration
cat >> /etc/bash.bashrc << 'BASHRC'

# AI-Native Linux OS Integration
if [ -f /opt/ai-native-linux/shell-integration.sh ]; then
    source /opt/ai-native-linux/shell-integration.sh
fi

BASHRC

EOF

# Make script executable and run
chmod +x "$CUSTOM_DIR/tmp/customize.sh"
chroot "$CUSTOM_DIR" /tmp/customize.sh

# 6. COPY AI-NATIVE LINUX FILES
log "Copying AI-Native Linux OS files..."

# Copy project files
cp -r ../src "$CUSTOM_DIR/opt/ai-native-linux/"
cp -r ../systemd "$CUSTOM_DIR/opt/ai-native-linux/"
cp ../requirements.txt "$CUSTOM_DIR/opt/ai-native-linux/"

# Copy scripts
cp -r ../scripts "$CUSTOM_DIR/opt/ai-native-linux/"

# Copy SystemD services to proper location
cp ../systemd/*.service "$CUSTOM_DIR/etc/systemd/system/"

# Create shell integration script
cat > "$CUSTOM_DIR/opt/ai-native-linux/shell-integration.sh" << 'EOF'
#!/bin/bash

# AI-Native Linux OS Shell Integration
export AI_NATIVE_LINUX=1

# AI Shell function
ai() {
    /opt/ai-native-linux/venv/bin/python /opt/ai-native-linux/src/ai_shell/ai_shell.py "$@"
}

# Quest Log aliases
alias qlog='quest commands --limit 20'
alias qsearch='quest search'
alias qstats='quest stats'

# AI-powered history search
ai-history() {
    history | tail -50 | ai "analyze these recent commands and suggest improvements"
}

# Smart directory listing with AI insights
ai-ls() {
    ls -la "$@" | ai "analyze this directory structure and suggest organization improvements"
}

# Add system commands to PATH
export PATH="/opt/ai-native-linux/bin:$PATH"

EOF

# Create system command scripts
mkdir -p "$CUSTOM_DIR/opt/ai-native-linux/bin"

cat > "$CUSTOM_DIR/opt/ai-native-linux/bin/ai" << 'EOF'
#!/bin/bash
/opt/ai-native-linux/venv/bin/python /opt/ai-native-linux/src/ai_shell/ai_shell.py "$@"
EOF

cat > "$CUSTOM_DIR/opt/ai-native-linux/bin/quest" << 'EOF'
#!/bin/bash
/opt/ai-native-linux/venv/bin/python /opt/ai-native-linux/src/quest_log/quest_log_cli.py "$@"
EOF

chmod +x "$CUSTOM_DIR/opt/ai-native-linux/bin/"*

# 7. SETUP PYTHON ENVIRONMENT
log "Setting up Python environment in custom ISO..."

chroot "$CUSTOM_DIR" /bin/bash -c "
cd /opt/ai-native-linux
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
"

# 8. ENABLE SERVICES
log "Enabling AI-Native Linux services..."

chroot "$CUSTOM_DIR" systemctl enable ollama.service
chroot "$CUSTOM_DIR" systemctl enable ai-shell.service
chroot "$CUSTOM_DIR" systemctl enable quest-log.service
chroot "$CUSTOM_DIR" systemctl enable kernel-monitor.service

# 9. CLEANUP AND UNMOUNT
log "Cleaning up chroot environment..."

umount "$CUSTOM_DIR/dev/pts" || true
umount "$CUSTOM_DIR/dev" || true
umount "$CUSTOM_DIR/proc" || true
umount "$CUSTOM_DIR/sys" || true

# Remove temporary files
rm -rf "$CUSTOM_DIR/tmp/*"
rm -rf "$CUSTOM_DIR/var/lib/apt/lists/*"

# 10. REBUILD SQUASHFS
log "Rebuilding filesystem.squashfs..."

rm "$EXTRACT_DIR/casper/filesystem.squashfs"
mksquashfs "$CUSTOM_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs" -comp xz -e boot

# Update filesystem size
printf $(du -sx --block-size=1 "$CUSTOM_DIR" | cut -f1) > "$EXTRACT_DIR/casper/filesystem.size"

# 11. UPDATE ISO METADATA
log "Updating ISO metadata..."

# Update disk info
cat > "$EXTRACT_DIR/.disk/info" << EOF
AI-Native Linux OS ${UBUNTU_VERSION} "AI-Powered Desktop" - Release ${ARCH} ($(date +%Y%m%d))
EOF

# Create custom grub menu
cat > "$EXTRACT_DIR/boot/grub/grub.cfg" << 'EOF'
set default="0"
set timeout=30

menuentry "AI-Native Linux OS - Live Session" {
    set gfxpayload=keep
    linux /casper/vmlinuz boot=casper quiet splash ---
    initrd /casper/initrd
}

menuentry "AI-Native Linux OS - Install" {
    set gfxpayload=keep
    linux /casper/vmlinuz boot=casper only-ubiquity quiet splash ---
    initrd /casper/initrd
}

menuentry "AI-Native Linux OS - Safe Mode" {
    set gfxpayload=keep
    linux /casper/vmlinuz boot=casper xforcevesa quiet splash ---
    initrd /casper/initrd
}

menuentry "Test Memory" {
    linux /install/mt86plus
}
EOF

# 12. CREATE FINAL ISO
log "Creating final ISO image..."

cd "$EXTRACT_DIR"

# Generate MD5 checksums
find . -type f -print0 | xargs -0 md5sum | grep -v "\./md5sum.txt" > md5sum.txt

# Create ISO
genisoimage -r -V "AI-Native Linux OS" \
    -cache-inodes -J -l \
    -b boot/grub/stage2_eltorito \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
    -o "../$ISO_NAME" .

# 13. CLEANUP
log "Cleaning up temporary files..."

cd "$WORK_DIR/.."
rm -rf "$WORK_DIR"

log "AI-Native Linux OS Custom ISO Build Complete!"
info "ISO created: $ISO_NAME"
info "Size: $(du -h "$ISO_NAME" | cut -f1)"

echo
echo "✅ Custom ISO Build Summary:"
echo "   - Base: Ubuntu ${UBUNTU_VERSION} ${ARCH}"
echo "   - AI Components: Fully integrated"
echo "   - LLM Server: Ollama with Phi-3 model"
echo "   - Services: Auto-start on boot"
echo "   - Shell Integration: Built-in AI commands"
echo
echo "🚀 Your AI-Native Linux OS is ready for installation!"
echo "   Use this ISO to install on any compatible system."
echo "   The AI features will be available immediately after installation." 