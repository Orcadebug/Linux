#!/bin/bash

# AI-Native Linux OS Installation Script

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/ai-native-linux"
SERVICE_DIR="/etc/systemd/system"
BIN_DIR="/usr/local/bin"

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
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        error "pip3 is required but not installed"
    fi
    
    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        error "systemd is required but not found"
    fi
}

install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package lists
    apt-get update -y
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        curl \
        wget \
        htop \
        git \
        build-essential \
        python3-dev
    
    log "System dependencies installed"
}

install_python_dependencies() {
    log "Installing Python dependencies..."
    
    # Install Python packages
    pip3 install -r "$PROJECT_ROOT/requirements.txt"
    
    log "Python dependencies installed"
}

install_components() {
    log "Installing AI-Native Linux components..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Copy source files
    cp -r "$PROJECT_ROOT/src" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/requirements.txt" "$INSTALL_DIR/"
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    
    # Make scripts executable
    chmod +x "$INSTALL_DIR/src/ai_shell/ai_shell.py"
    chmod +x "$INSTALL_DIR/src/quest_log/quest_log_daemon.py"
    chmod +x "$INSTALL_DIR/src/quest_log/quest_log_cli.py"
    chmod +x "$INSTALL_DIR/src/kernel_monitor/kernel_monitor.py"
    chmod +x "$INSTALL_DIR/src/self_healing/self_healing_service.py"
    
    log "Components installed to $INSTALL_DIR"
}

create_symlinks() {
    log "Creating command symlinks..."
    
    # Create symlinks for easy access
    ln -sf "$INSTALL_DIR/src/ai_shell/ai_shell.py" "$BIN_DIR/ai"
    ln -sf "$INSTALL_DIR/src/quest_log/quest_log_cli.py" "$BIN_DIR/quest"
    
    log "Command symlinks created"
}

install_systemd_services() {
    log "Installing systemd services..."
    
    # Quest Log Daemon
    cat > "$SERVICE_DIR/quest-log-daemon.service" << EOF
[Unit]
Description=Quest Log Daemon
After=network.target
Wants=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
ExecStart=/usr/bin/python3 $INSTALL_DIR/src/quest_log/quest_log_daemon.py --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Kernel Monitor
    cat > "$SERVICE_DIR/kernel-monitor.service" << EOF
[Unit]
Description=AI Kernel Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
ExecStart=/usr/bin/python3 $INSTALL_DIR/src/kernel_monitor/kernel_monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Self-Healing Service
    cat > "$SERVICE_DIR/self-healing-service.service" << EOF
[Unit]
Description=Self-Healing Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/bin/python3 $INSTALL_DIR/src/self_healing/self_healing_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    log "Systemd services installed"
}

configure_shell_integration() {
    log "Configuring shell integration..."
    
    # Create profile.d script for system-wide integration
    cat > /etc/profile.d/ai-native-linux.sh << 'EOF'
# AI-Native Linux OS Integration

# Add AI tools to PATH
export PATH="/opt/ai-native-linux/src:$PATH"

# AI Shell Assistant alias
alias ai='python3 /opt/ai-native-linux/src/ai_shell/ai_shell.py'

# Quest Log aliases
alias quest='python3 /opt/ai-native-linux/src/quest_log/quest_log_cli.py'
alias qlog='quest commands --limit 10'
alias qsearch='quest search'

# Show welcome message for interactive shells
if [ "$PS1" ] && [ -z "$AI_NATIVE_WELCOME_SHOWN" ]; then
    echo "Welcome to AI-Native Linux OS!"
    echo "Available commands:"
    echo "  ai <query>     - AI Shell Assistant"
    echo "  quest          - Quest Log viewer"
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
    
    # Create config directory
    mkdir -p /etc/ai-native-linux
    
    # AI Shell Assistant config
    cat > /etc/ai-native-linux/ai_shell.json << EOF
{
    "llm_provider": "local",
    "max_history": 100,
    "safety_check": true,
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
    "log_file": "/var/log/kernel_monitor.log"
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
            "name": "quest-log-daemon",
            "command": "systemctl start quest-log-daemon",
            "check_command": "systemctl is-active quest-log-daemon",
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
    "log_file": "/var/log/self_healing.log",
    "max_restart_window": 3600
}
EOF
    
    # Set permissions
    chown -R root:root /etc/ai-native-linux
    chmod -R 644 /etc/ai-native-linux/*.json
    
    log "Configuration files created"
}

enable_services() {
    log "Enabling and starting services..."
    
    # Enable services
    systemctl enable quest-log-daemon
    systemctl enable kernel-monitor
    systemctl enable self-healing-service
    
    # Start services
    systemctl start quest-log-daemon
    systemctl start kernel-monitor
    systemctl start self-healing-service
    
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
    
    # Check service status
    services=("quest-log-daemon" "kernel-monitor" "self-healing-service")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            info "✓ $service is running"
        else
            warn "✗ $service is not running"
        fi
    done
    
    log "Installation verification completed"
}

show_usage_info() {
    info "AI-Native Linux OS installed successfully!"
    echo ""
    echo "Available commands:"
    echo "  ai <query>     - AI Shell Assistant"
    echo "  quest          - Quest Log viewer"
    echo "  qlog           - Recent commands"
    echo "  qsearch <term> - Search logs"
    echo ""
    echo "Services:"
    echo "  quest-log-daemon   - System activity logging"
    echo "  kernel-monitor     - System monitoring with AI"
    echo "  self-healing-service - Automatic service recovery"
    echo ""
    echo "Configuration files:"
    echo "  /etc/ai-native-linux/*.json"
    echo ""
    echo "Logs:"
    echo "  /var/log/kernel_monitor.log"
    echo "  /var/log/self_healing.log"
    echo "  journalctl -u quest-log-daemon"
    echo "  journalctl -u kernel-monitor"
    echo "  journalctl -u self-healing-service"
    echo ""
    echo "To get started, try: ai list files"
}

main() {
    log "Starting AI-Native Linux OS installation..."
    
    check_requirements
    install_dependencies
    install_python_dependencies
    install_components
    create_symlinks
    install_systemd_services
    configure_shell_integration
    create_configuration_files
    enable_services
    verify_installation
    show_usage_info
    
    log "Installation completed successfully!"
}

# Handle script arguments
case "$1" in
    --uninstall)
        log "Uninstalling AI-Native Linux OS..."
        
        # Stop and disable services
        systemctl stop quest-log-daemon kernel-monitor self-healing-service || true
        systemctl disable quest-log-daemon kernel-monitor self-healing-service || true
        
        # Remove service files
        rm -f "$SERVICE_DIR/quest-log-daemon.service"
        rm -f "$SERVICE_DIR/kernel-monitor.service"
        rm -f "$SERVICE_DIR/self-healing-service.service"
        
        # Remove installation
        rm -rf "$INSTALL_DIR"
        rm -f "$BIN_DIR/ai"
        rm -f "$BIN_DIR/quest"
        rm -f /etc/profile.d/ai-native-linux.sh
        rm -rf /etc/ai-native-linux
        
        # Reload systemd
        systemctl daemon-reload
        
        log "Uninstallation completed"
        ;;
    --help)
        echo "AI-Native Linux OS Installation Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --uninstall    Remove AI-Native Linux OS"
        echo "  --help         Show this help message"
        echo ""
        ;;
    *)
        main "$@"
        ;;
esac