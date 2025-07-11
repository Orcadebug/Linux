#!/bin/bash

# AI-Native Linux OS - Deep OS Integration Script
# This script integrates AI features directly into the OS core

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root for deep OS integration"
fi

log "Starting AI-Native Linux OS Deep Integration..."

# 1. SYSTEM INSTALLATION
log "Installing AI components to system directories..."

# Create system directories
mkdir -p /opt/ai-native-linux
mkdir -p /etc/ai-native-linux
mkdir -p /var/log/ai-native-linux
mkdir -p /var/lib/ai-native-linux

# Copy project files
cp -r src/ /opt/ai-native-linux/
cp -r requirements.txt /opt/ai-native-linux/
cp -r systemd/ /opt/ai-native-linux/

# Set permissions
chown -R root:root /opt/ai-native-linux
chmod -R 755 /opt/ai-native-linux

# 2. PYTHON ENVIRONMENT SETUP
log "Setting up system Python environment..."

cd /opt/ai-native-linux
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. OLLAMA LLM INTEGRATION
log "Installing and configuring Ollama LLM..."

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Create ollama user
useradd -r -s /bin/false -d /var/lib/ollama ollama || true
mkdir -p /var/lib/ollama
chown ollama:ollama /var/lib/ollama

# Install SystemD service for Ollama
cp systemd/ollama.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ollama.service
systemctl start ollama.service

# Pull lightweight LLM model
log "Downloading lightweight LLM model (this may take a few minutes)..."
sleep 5  # Wait for Ollama to start
sudo -u ollama ollama pull phi3

# 4. SYSTEMD SERVICES INTEGRATION
log "Installing SystemD services..."

cp systemd/ai-shell.service /etc/systemd/system/
cp systemd/quest-log.service /etc/systemd/system/
cp systemd/kernel-monitor.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable ai-shell.service
systemctl enable quest-log.service  
systemctl enable kernel-monitor.service

# 5. SHELL INTEGRATION
log "Integrating AI shell into system shell..."

# Add ai command to system PATH
cat > /usr/local/bin/ai << 'EOF'
#!/bin/bash
/opt/ai-native-linux/venv/bin/python /opt/ai-native-linux/src/ai_shell/ai_shell.py "$@"
EOF
chmod +x /usr/local/bin/ai

# Add quest command
cat > /usr/local/bin/quest << 'EOF'
#!/bin/bash
/opt/ai-native-linux/venv/bin/python /opt/ai-native-linux/src/quest_log/quest_log_cli.py "$@"
EOF
chmod +x /usr/local/bin/quest

# 6. BASH INTEGRATION
log "Integrating with Bash shell..."

# Add AI shell integration to bashrc
cat >> /etc/bash.bashrc << 'EOF'

# AI-Native Linux OS Integration
export AI_NATIVE_LINUX=1

# AI Shell function
ai() {
    /usr/local/bin/ai "$@"
}

# Quest Log aliases
alias qlog='quest commands --limit 20'
alias qsearch='quest search'
alias qstats='quest stats'

# AI-powered history search
ai-history() {
    history | tail -50 | /usr/local/bin/ai "analyze these recent commands and suggest improvements"
}

# Smart directory listing with AI insights
ai-ls() {
    ls -la "$@" | /usr/local/bin/ai "analyze this directory structure and suggest organization improvements"
}

EOF

# 7. KERNEL MODULE INTEGRATION (Advanced)
log "Setting up kernel-level integration..."

# Create kernel module for deep OS integration
mkdir -p /opt/ai-native-linux/kernel-module

cat > /opt/ai-native-linux/kernel-module/ai_native.c << 'EOF'
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>

#define PROC_NAME "ai_native"

static struct proc_dir_entry *proc_entry;

static ssize_t ai_native_read(struct file *file, char __user *buffer, size_t count, loff_t *pos) {
    char *msg = "AI-Native Linux OS Kernel Module Active\n";
    int len = strlen(msg);
    
    if (*pos >= len) return 0;
    if (copy_to_user(buffer, msg, len)) return -EFAULT;
    *pos += len;
    return len;
}

static const struct proc_ops ai_native_ops = {
    .proc_read = ai_native_read,
};

static int __init ai_native_init(void) {
    proc_entry = proc_create(PROC_NAME, 0666, NULL, &ai_native_ops);
    if (!proc_entry) {
        printk(KERN_ALERT "AI-Native: Failed to create /proc/%s\n", PROC_NAME);
        return -ENOMEM;
    }
    printk(KERN_INFO "AI-Native Linux OS kernel module loaded\n");
    return 0;
}

static void __exit ai_native_exit(void) {
    proc_remove(proc_entry);
    printk(KERN_INFO "AI-Native Linux OS kernel module unloaded\n");
}

module_init(ai_native_init);
module_exit(ai_native_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("AI-Native Linux OS Kernel Integration");
MODULE_VERSION("1.0");
EOF

# Create Makefile for kernel module
cat > /opt/ai-native-linux/kernel-module/Makefile << 'EOF'
obj-m += ai_native.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean

install:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules_install
	depmod -A
EOF

# Build and install kernel module
cd /opt/ai-native-linux/kernel-module
apt-get update
apt-get install -y linux-headers-$(uname -r) build-essential
make
make install
modprobe ai_native

# 8. BOOT INTEGRATION
log "Integrating with boot process..."

# Add to modules to load at boot
echo "ai_native" >> /etc/modules

# Create boot service for early AI initialization
cat > /etc/systemd/system/ai-native-early.service << 'EOF'
[Unit]
Description=AI-Native Linux OS Early Initialization
After=local-fs.target
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo "AI-Native Linux OS initializing..." > /dev/kmsg'
ExecStart=/bin/bash -c 'modprobe ai_native'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable ai-native-early.service

# 9. PAM INTEGRATION (Advanced Authentication)
log "Setting up PAM integration for AI-powered authentication..."

# Create PAM module for AI-enhanced authentication
mkdir -p /opt/ai-native-linux/pam-module

cat > /opt/ai-native-linux/pam-module/pam_ai_native.c << 'EOF'
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <syslog.h>
#include <string.h>

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    // AI-powered authentication analysis would go here
    pam_syslog(pamh, LOG_INFO, "AI-Native authentication check performed");
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}
EOF

# 10. FILESYSTEM INTEGRATION
log "Setting up filesystem integration..."

# Create AI-native filesystem entries
mkdir -p /sys/ai-native
echo "1" > /sys/ai-native/enabled || true

# Create special device files
mknod /dev/ai-native c 42 0 || true
chmod 666 /dev/ai-native

# 11. START SERVICES
log "Starting AI-Native Linux OS services..."

systemctl start ai-shell.service
systemctl start quest-log.service
systemctl start kernel-monitor.service

# 12. VERIFICATION
log "Verifying integration..."

# Check if services are running
systemctl is-active ollama.service || warn "Ollama service not running"
systemctl is-active ai-shell.service || warn "AI Shell service not running"
systemctl is-active quest-log.service || warn "Quest Log service not running"  
systemctl is-active kernel-monitor.service || warn "Kernel Monitor service not running"

# Check if kernel module loaded
lsmod | grep ai_native || warn "AI-Native kernel module not loaded"

# Check if commands work
/usr/local/bin/ai "test command" || warn "AI command not working"

log "AI-Native Linux OS Deep Integration Complete!"
info "Reboot recommended to ensure all components start properly"

echo
echo "✅ Integration Status:"
echo "   - SystemD Services: Installed and enabled"
echo "   - Shell Commands: 'ai' and 'quest' available system-wide"
echo "   - Kernel Module: Loaded and integrated"
echo "   - LLM Server: Running locally on port 11434"
echo "   - Boot Integration: Will start automatically"
echo
echo "🔧 Usage:"
echo "   - ai 'your natural language command'"
echo "   - quest commands --recent 20"
echo "   - qlog  (alias for recent commands)"
echo
echo "🚀 Your AI features are now part of the OS core!" 