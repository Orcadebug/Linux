#!/bin/bash
# AI-Native Linux OS - Consolidated Installation Script
# Merges functionality from install.sh, install-ai-terminal.sh, os-integration.sh, and install-system-integration.sh

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/ai-native-linux"
SERVICE_DIR="/etc/systemd/system"
BIN_DIR="/usr/local/bin"
AI_OS_DIR="/usr/local/ai-native-os"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root (use sudo)"
    fi
    
    # Check OS
    if [ ! -f /etc/os-release ]; then
        error "Cannot determine OS version"
    fi
    
    source /etc/os-release
    info "Detected OS: $NAME $VERSION"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python3 is required but not installed"
    fi
    
    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        error "systemd is required but not found"
    fi
    
    log "System requirements check passed"
}

install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package lists
    apt-get update -y
    
    # Install essential packages (consolidated from all scripts)
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-full \
        python3-tk \
        git \
        curl \
        wget \
        htop \
        tree \
        build-essential \
        linux-headers-generic \
        libsqlite3-dev \
        sqlite3
    
    log "System dependencies installed"
}

install_ollama() {
    log "Installing and configuring Ollama LLM..."
    
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Create ollama user
    useradd -r -s /bin/false -d /var/lib/ollama ollama || true
    mkdir -p /var/lib/ollama
    chown ollama:ollama /var/lib/ollama
    
    # Hardware scanning and model selection (from os-integration.sh)
    log "Scanning hardware to select best LLM model..."
    RAM_GB=$(awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
    CPU_CORES=$(nproc)
    
    MODEL="phi3"  # Default
    if [ "$RAM_GB" -lt 4 ]; then
        MODEL="tinyllm"
        log "Detected $RAM_GB GB RAM: Using TinyLLM (1.1GB, fastest, lowest resource)"
    elif [ "$RAM_GB" -lt 8 ]; then
        MODEL="phi3"
        log "Detected $RAM_GB GB RAM: Using Phi-3 (2.2GB, good balance)"
    elif [ "$RAM_GB" -lt 16 ]; then
        MODEL="mistral"
        log "Detected $RAM_GB GB RAM: Using Mistral (4.1GB, higher quality)"
    else
        MODEL="llama3"
        log "Detected $RAM_GB GB RAM: Using Llama 3 (4.7GB, best quality)"
    fi
    
    # Pull the selected model
    log "Pulling Ollama model: $MODEL (this may take a few minutes)..."
    sleep 5  # Wait for Ollama to start
    sudo -u ollama ollama pull $MODEL || warn "Failed to pull model $MODEL"
    
    log "Ollama installation completed"
}

install_core_components() {
    log "Installing AI-Native Linux core components..."
    
    # Create installation directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$AI_OS_DIR"/{bin,lib,share,models,logs}
    mkdir -p "$AI_OS_DIR/lib/python"
    mkdir -p "$AI_OS_DIR/share/web_interface"
    mkdir -p /etc/ai-native-linux
    mkdir -p /var/log/ai-native-linux
    mkdir -p /var/lib/ai-native-linux
    
    # Copy source files
    cp -r "$PROJECT_ROOT/src" "$INSTALL_DIR/"
    cp -r "$PROJECT_ROOT/src/web_interface" "$AI_OS_DIR/share/" 2>/dev/null || true
    cp "$PROJECT_ROOT/requirements.txt" "$INSTALL_DIR/"
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    
    # Make scripts executable
    find "$INSTALL_DIR/src" -name "*.py" -exec chmod +x {} \;
    
    log "Core components installed to $INSTALL_DIR"
}

setup_python_environment() {
    log "Setting up Python environment..."
    
    # Create virtual environment
    cd "$INSTALL_DIR"
    python3 -m venv venv
    source venv/bin/activate
    
    # Install Python dependencies
    pip install --upgrade pip
    pip install -r "$PROJECT_ROOT/requirements.txt"
    
    # Additional dependencies from various scripts
    pip install ollama transformers torch psutil click requests aiofiles aiohttp cryptography
    
    log "Python environment setup completed"
}

create_system_commands() {
    log "Creating system commands..."
    
    # AI Shell command
    cat > "$BIN_DIR/ai" << 'EOF'
#!/bin/bash
cd /opt/ai-native-linux
source venv/bin/activate
python src/ai_orchestrator/main_ai_controller.py "$@"
EOF
    
    # Quest Log command
    cat > "$BIN_DIR/quest" << 'EOF'
#!/bin/bash
cd /opt/ai-native-linux
source venv/bin/activate
python src/quest_log/quest_log_cli.py "$@"
EOF
    
    # AI Terminal GUI command
    cat > "$BIN_DIR/ai-terminal" << 'EOF'
#!/bin/bash
cd /opt/ai-native-linux
source venv/bin/activate
python src/ai_shell/ai_terminal_gui.py "$@"
EOF
    
    # Make commands executable
    chmod +x "$BIN_DIR/ai"
    chmod +x "$BIN_DIR/quest"
    chmod +x "$BIN_DIR/ai-terminal"
    
    log "System commands created"
}

install_ai_terminal_gui() {
    log "Installing AI Terminal GUI..."
    
    # Create AI Terminal directory
    mkdir -p /opt/ai-terminal
    
    # Copy AI Terminal files
    cp -r "$PROJECT_ROOT/src/ai_shell/"* /opt/ai-terminal/ 2>/dev/null || true
    chmod +x /opt/ai-terminal/launch_ai_terminal.sh 2>/dev/null || true
    
    # Install desktop entry
    if [ -f "$PROJECT_ROOT/ai-terminal.desktop" ]; then
        cp "$PROJECT_ROOT/ai-terminal.desktop" /usr/share/applications/
        chmod 644 /usr/share/applications/ai-terminal.desktop
        
        # Update desktop database
        if command -v update-desktop-database &> /dev/null; then
            update-desktop-database /usr/share/applications/
        fi
    fi
    
    log "AI Terminal GUI installed"
}

install_systemd_services() {
    log "Installing systemd services..."
    
    # AI Shell Service
    cat > "$SERVICE_DIR/ai-shell.service" << EOF
[Unit]
Description=AI-Native Linux Shell Service
After=network.target ollama.service
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/ai_shell/ai_shell_daemon.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Quest Log Service
    cat > "$SERVICE_DIR/quest-log.service" << EOF
[Unit]
Description=AI-Native Linux Quest Log Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/quest_log/quest_log_daemon.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Kernel Monitor Service
    cat > "$SERVICE_DIR/kernel-monitor.service" << EOF
[Unit]
Description=AI-Native Linux Kernel Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/kernel_monitor/kernel_monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Self-Healing Service
    cat > "$SERVICE_DIR/self-healing.service" << EOF
[Unit]
Description=AI-Native Linux Self-Healing Service
After=network.target quest-log.service
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/self_healing/self_healing_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Ollama Service (if not already exists)
    if [ ! -f "$SERVICE_DIR/ollama.service" ]; then
        cat > "$SERVICE_DIR/ollama.service" << EOF
[Unit]
Description=Ollama Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ollama
Group=ollama
ExecStart=/usr/local/bin/ollama serve
Environment=OLLAMA_HOST=127.0.0.1:11434
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    fi
    
    log "SystemD services installed"
}

configure_shell_integration() {
    log "Configuring shell integration..."
    
    # Create profile.d script for system-wide integration
    cat > /etc/profile.d/ai-native-linux.sh << 'EOF'
# AI-Native Linux OS Integration

# Add AI tools to PATH
export PATH="/opt/ai-native-linux/bin:$PATH"

# AI Shell Assistant alias
alias ai='ai'

# Quest Log aliases
alias quest='quest'
alias qlog='quest commands --limit 10'
alias qsearch='quest search'

# AI-powered history search
ai-history() {
    history | tail -50 | ai "analyze these recent commands and suggest improvements"
}

# Smart directory listing with AI insights
ai-ls() {
    ls -la "$@" | ai "analyze this directory structure and suggest organization improvements"
}

# Show welcome message for interactive shells
if [ "$PS1" ] && [ -z "$AI_NATIVE_WELCOME_SHOWN" ]; then
    echo "Welcome to AI-Native Linux OS!"
    echo "Available commands:"
    echo "  ai <query>     - AI Shell Assistant"
    echo "  quest          - Quest Log viewer"
    echo "  ai-terminal    - AI Terminal GUI"
    echo "  qlog           - Recent commands"
    echo "  qsearch <term> - Search logs"
    echo ""
    export AI_NATIVE_WELCOME_SHOWN=1
fi
EOF
    
    chmod +x /etc/profile.d/ai-native-linux.sh
    
    log "Shell integration configured"
}

create_configuration_files() {
    log "Creating configuration files..."
    
    # Main AI configuration
    cat > /etc/ai-native-linux/main_config.json << EOF
{
    "ai_classification": true,
    "auto_fix_enabled": true,
    "max_concurrent_tasks": 5,
    "task_timeout": 300,
    "log_level": "INFO",
    "security": {
        "require_confirmation": true,
        "dangerous_commands": ["rm -rf", "dd if=", "mkfs", "format", "fdisk"],
        "max_privilege_escalation": 1
    },
    "agents": {
        "system_agent": {"enabled": true, "max_tasks": 2},
        "file_management_agent": {"enabled": true, "max_tasks": 3},
        "software_install_agent": {"enabled": true, "max_tasks": 1},
        "shell_assistant_agent": {"enabled": true, "max_tasks": 2},
        "activity_tracker_agent": {"enabled": true, "max_tasks": 1},
        "troubleshooting_agent": {"enabled": true, "max_tasks": 2}
    }
}
EOF
    
    # AI Shell Assistant config
    cat > /etc/ai-native-linux/ai_shell.json << EOF
{
    "llm_provider": "local",
    "max_history": 100,
    "safety_check": true,
    "auto_execute": false,
    "context_aware": true,
    "beginner_mode": true,
    "dangerous_commands": [
        "rm -rf",
        "dd if=",
        "mkfs",
        "format",
        "fdisk",
        "parted",
        "shutdown",
        "reboot"
    ]
}
EOF
    
    # Kernel Monitor config
    cat > /etc/ai-native-linux/kernel_monitor.json << EOF
{
    "cpu_threshold": 80.0,
    "memory_threshold": 85.0,
    "disk_threshold": 90.0,
    "network_threshold": 100.0,
    "check_interval": 5,
    "anomaly_detection": true,
    "alert_cooldown": 300,
    "log_file": "/var/log/ai-native-linux/kernel_monitor.log"
}
EOF
    
    # Self-Healing Service config
    cat > /etc/ai-native-linux/self_healing.json << EOF
{
    "services": [
        {
            "name": "sshd",
            "command": "systemctl start sshd",
            "check_command": "systemctl is-active sshd",
            "critical": true,
            "max_restarts": 3,
            "restart_delay": 30
        },
        {
            "name": "quest-log",
            "command": "systemctl start quest-log",
            "check_command": "systemctl is-active quest-log",
            "critical": true,
            "max_restarts": 5,
            "restart_delay": 10
        },
        {
            "name": "kernel-monitor",
            "command": "systemctl start kernel-monitor",
            "check_command": "systemctl is-active kernel-monitor",
            "critical": true,
            "max_restarts": 5,
            "restart_delay": 10
        }
    ],
    "processes": [],
    "check_interval": 30,
    "log_file": "/var/log/ai-native-linux/self_healing.log",
    "max_restart_window": 3600
}
EOF
    
    # Set permissions
    chown -R root:root /etc/ai-native-linux
    chmod -R 644 /etc/ai-native-linux/*.json
    
    log "Configuration files created"
}

setup_log_rotation() {
    log "Setting up log rotation..."
    
    cat > /etc/logrotate.d/ai-native-linux << EOF
/var/log/ai-native-linux/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    create 644 root root
}
EOF
    
    log "Log rotation configured"
}

enable_and_start_services() {
    log "Enabling and starting services..."
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable ollama.service
    systemctl enable ai-shell.service
    systemctl enable quest-log.service
    systemctl enable kernel-monitor.service
    systemctl enable self-healing.service
    
    # Start services
    systemctl start ollama.service
    sleep 5  # Wait for Ollama to start
    systemctl start ai-shell.service
    systemctl start quest-log.service
    systemctl start kernel-monitor.service
    systemctl start self-healing.service
    
    log "Services enabled and started"
}

verify_installation() {
    log "Verifying installation..."
    
    # Check if commands are available
    if command -v ai &> /dev/null; then
        info "✓ AI Shell Assistant command available"
    else
        warn "✗ AI Shell Assistant command not available"
    fi
    
    if command -v quest &> /dev/null; then
        info "✓ Quest Log CLI command available"
    else
        warn "✗ Quest Log CLI command not available"
    fi
    
    if command -v ai-terminal &> /dev/null; then
        info "✓ AI Terminal GUI command available"
    else
        warn "✗ AI Terminal GUI command not available"
    fi
    
    # Check service status
    services=("ollama" "ai-shell" "quest-log" "kernel-monitor" "self-healing")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            info "✓ $service service is running"
        else
            warn "✗ $service service is not running"
        fi
    done
    
    log "Installation verification completed"
}

show_usage_info() {
    info "AI-Native Linux OS installed successfully!"
    echo ""
    echo "🚀 Available commands:"
    echo "  ai <query>       - AI Shell Assistant with natural language processing"
    echo "  quest            - Quest Log viewer for command history and insights"
    echo "  ai-terminal      - AI Terminal GUI application"
    echo "  qlog             - Recent commands with AI analysis"
    echo "  qsearch <term>   - Search command history"
    echo "  ai-history       - AI-powered history analysis"
    echo "  ai-ls            - Smart directory listing with AI insights"
    echo ""
    echo "🔧 Services:"
    echo "  ollama           - Local LLM server (model: $MODEL)"
    echo "  ai-shell         - AI shell integration service"
    echo "  quest-log        - System activity logging with AI analysis"
    echo "  kernel-monitor   - System monitoring with AI insights"
    echo "  self-healing     - Automatic service recovery"
    echo ""
    echo "📁 Configuration files:"
    echo "  /etc/ai-native-linux/*.json"
    echo ""
    echo "📊 Logs:"
    echo "  /var/log/ai-native-linux/"
    echo "  journalctl -u <service-name>"
    echo ""
    echo "🎯 Quick Start:"
    echo "  Try: ai \"list my files\""
    echo "  Try: ai \"fix network issues\""
    echo "  Try: ai \"install docker\""
    echo "  Try: quest commands --recent"
    echo ""
    echo "💡 The AI learns from your usage patterns and provides intelligent suggestions!"
}

install_core() {
    log "Installing core AI-Native Linux OS components..."
    
    check_requirements
    install_dependencies
    install_ollama
    install_core_components
    setup_python_environment
    create_system_commands
    install_systemd_services
    configure_shell_integration
    create_configuration_files
    setup_log_rotation
    enable_and_start_services
    verify_installation
    
    log "Core installation completed"
}

install_gui() {
    log "Installing GUI components..."
    
    install_ai_terminal_gui
    
    log "GUI installation completed"
}

install_advanced() {
    log "Installing advanced components..."
    
    # Kernel module integration (optional)
    if [ "$INSTALL_KERNEL_MODULE" = "true" ]; then
        log "Installing kernel module..."
        
        # Create kernel module directory
        mkdir -p /opt/ai-native-linux/kernel-module
        
        # Create basic kernel module
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
        
        # Create Makefile
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
        make && make install
        modprobe ai_native
        echo "ai_native" >> /etc/modules
        
        log "Kernel module installed"
    fi
    
    log "Advanced installation completed"
}

uninstall() {
    log "Uninstalling AI-Native Linux OS..."
    
    # Stop and disable services
    systemctl stop ai-shell quest-log kernel-monitor self-healing ollama || true
    systemctl disable ai-shell quest-log kernel-monitor self-healing ollama || true
    
    # Remove service files
    rm -f "$SERVICE_DIR/ai-shell.service"
    rm -f "$SERVICE_DIR/quest-log.service"
    rm -f "$SERVICE_DIR/kernel-monitor.service"
    rm -f "$SERVICE_DIR/self-healing.service"
    
    # Remove installation directories
    rm -rf "$INSTALL_DIR"
    rm -rf "$AI_OS_DIR"
    rm -rf /opt/ai-terminal
    
    # Remove commands
    rm -f "$BIN_DIR/ai"
    rm -f "$BIN_DIR/quest"
    rm -f "$BIN_DIR/ai-terminal"
    
    # Remove configuration
    rm -rf /etc/ai-native-linux
    rm -f /etc/profile.d/ai-native-linux.sh
    rm -f /etc/logrotate.d/ai-native-linux
    
    # Remove desktop entry
    rm -f /usr/share/applications/ai-terminal.desktop
    
    # Remove kernel module
    rmmod ai_native 2>/dev/null || true
    rm -rf /opt/ai-native-linux/kernel-module
    
    # Reload systemd
    systemctl daemon-reload
    
    log "Uninstallation completed"
}

main() {
    case "$1" in
        --core)
            install_core
            ;;
        --gui)
            install_gui
            ;;
        --advanced)
            INSTALL_KERNEL_MODULE=true
            install_advanced
            ;;
        --all)
            install_core
            install_gui
            install_advanced
            show_usage_info
            ;;
        --uninstall)
            uninstall
            ;;
        --help)
            echo "AI-Native Linux OS Installation Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --core       Install core AI components and services"
            echo "  --gui        Install GUI components (AI Terminal)"
            echo "  --advanced   Install advanced components (kernel module)"
            echo "  --all        Install everything (recommended)"
            echo "  --uninstall  Remove AI-Native Linux OS"
            echo "  --help       Show this help message"
            echo ""
            ;;
        *)
            log "Starting complete AI-Native Linux OS installation..."
            install_core
            install_gui
            show_usage_info
            ;;
    esac
}

# Run main function with all arguments
main "$@" 