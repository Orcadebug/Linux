#!/bin/bash

# AI-Native Linux OS - One-Fell-Swoop Installation Script
# Installs everything: dependencies, Ollama, models, components, symlinks, and systemd services.

set -e

# Configuration
INSTALL_DIR="/opt/ai-native-linux"
BIN_DIR="/usr/local/bin"
SERVICE_DIR="/etc/systemd/system"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIRED_PACKAGES="python3 python3-pip python3-venv git curl wget htop build-essential python3-dev sqlite3 python3-tk"
OLLAMA_MODEL="phi3:mini"  # Default tiny LLM; can be changed

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
        error "This script must be run as root (use sudo)."
    fi
    
    # Check OS
    if [ ! -f /etc/os-release ]; then
        error "Cannot determine OS version"
    fi
    
    source /etc/os-release
    info "Detected OS: $NAME $VERSION"
    
    # Check for Debian-based system
    if ! command -v apt-get &> /dev/null; then
        error "This script requires a Debian-based system with apt (e.g., Ubuntu)."
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        warn "Python3 not found, will be installed"
    fi
    
    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        error "systemd is required but not found."
    fi
    
    log "Requirements check passed."
}

install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package lists
    apt-get update -y
    
    # Install required packages
    apt-get install -y $REQUIRED_PACKAGES
    
    log "System dependencies installed."
}

setup_python_env() {
    log "Setting up Python environment..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip and install requirements
    pip install --upgrade pip
    pip install -r "$PROJECT_ROOT/requirements.txt"
    
    # Install additional dependencies for the mixture of agents
    pip install ollama transformers torch psutil click requests aiofiles aiohttp cryptography
    
    log "Python environment set up."
}

install_ollama() {
    log "Installing Ollama..."
    
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Create ollama user if it doesn't exist
    if ! id "ollama" &>/dev/null; then
        useradd -r -s /bin/false -d /var/lib/ollama ollama
        mkdir -p /var/lib/ollama
        chown ollama:ollama /var/lib/ollama
    fi
    
    # Start Ollama service
    systemctl enable ollama || true
    systemctl start ollama || true
    
    # Wait a moment for Ollama to start
    sleep 5
    
    # Pull the model
    log "Pulling Ollama model: $OLLAMA_MODEL..."
    ollama pull "$OLLAMA_MODEL" || warn "Failed to pull model, will be downloaded on first use"
    
    log "Ollama installed and configured."
}

install_components() {
    log "Installing AI-Native Linux components..."
    
    # Copy source files
    cp -r "$PROJECT_ROOT/src" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/requirements.txt" "$INSTALL_DIR/"
    
    # Copy systemd service files if they exist
    if [ -d "$PROJECT_ROOT/systemd" ]; then
        cp -r "$PROJECT_ROOT/systemd" "$INSTALL_DIR/"
    fi
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    
    # Make Python scripts executable
    find "$INSTALL_DIR/src" -name "*.py" -exec chmod +x {} \;
    
    # Create configuration directories
    mkdir -p /etc/ai-native-linux
    mkdir -p /var/log/ai-native-linux
    mkdir -p /var/lib/ai-native-linux
    
    log "Components installed to $INSTALL_DIR."
}

create_symlinks() {
    log "Creating command symlinks..."
    
    # AI Terminal GUI command
    cat > "$BIN_DIR/ai-terminal" << EOF
#!/bin/bash
cd $INSTALL_DIR
source venv/bin/activate
python src/ai_shell/ai_terminal_gui.py "\$@"
EOF
    
    # AI Shell command
    cat > "$BIN_DIR/ai" << EOF
#!/bin/bash
cd $INSTALL_DIR
source venv/bin/activate
python src/ai_orchestrator/main_ai_controller.py "\$@"
EOF
    
    # Quest Log command
    cat > "$BIN_DIR/quest" << EOF
#!/bin/bash
cd $INSTALL_DIR
source venv/bin/activate
python src/quest_log/quest_log_cli.py "\$@"
EOF
    
    # Make commands executable
    chmod +x "$BIN_DIR/ai-terminal"
    chmod +x "$BIN_DIR/ai"
    chmod +x "$BIN_DIR/quest"
    
    log "Command symlinks created."
}

install_systemd_services() {
    log "Installing systemd services..."
    
    # AI Orchestrator Service (Main AI Controller)
    cat > "$SERVICE_DIR/ai-orchestrator.service" << EOF
[Unit]
Description=AI-Native Linux Orchestrator Service
After=network.target ollama.service
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/ai_orchestrator/main_ai_controller.py --daemon
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
After=network.target quest-log.service
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
    
    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable ai-orchestrator.service
    systemctl enable quest-log.service
    systemctl enable kernel-monitor.service
    systemctl enable self-healing.service
    
    # Start services
    systemctl start quest-log.service
    systemctl start kernel-monitor.service
    systemctl start self-healing.service
    systemctl start ai-orchestrator.service
    
    log "Systemd services installed and started."
}

install_desktop_integration() {
    log "Installing desktop integration..."
    
    # Install desktop entry if available
    if [ -f "$PROJECT_ROOT/ai-terminal.desktop" ]; then
        cp "$PROJECT_ROOT/ai-terminal.desktop" /usr/share/applications/
        chmod 644 /usr/share/applications/ai-terminal.desktop
        
        # Update desktop database
        if command -v update-desktop-database &> /dev/null; then
            update-desktop-database /usr/share/applications/
        fi
        
        log "Desktop entry installed."
    fi
}

create_configuration_files() {
    log "Creating configuration files..."
    
    # AI Shell configuration
    cat > /etc/ai-native-linux/ai_shell.json << 'EOF'
{
    "llm_provider": "ollama",
    "ollama_host": "http://localhost:11434",
    "model": "phi3:mini",
    "max_history": 100,
    "safety_check": true,
    "dangerous_commands": ["rm -rf", "dd if=", "mkfs", "format"],
    "auto_execute": false,
    "log_commands": true
}
EOF
    
    # Quest Log configuration
    cat > /etc/ai-native-linux/quest_log.json << 'EOF'
{
    "log_file": "/var/log/ai-native-linux/quest_log.db",
    "max_entries": 10000,
    "cleanup_days": 30,
    "log_level": "INFO"
}
EOF
    
    # Kernel Monitor configuration
    cat > /etc/ai-native-linux/kernel_monitor.json << 'EOF'
{
    "cpu_threshold": 80.0,
    "memory_threshold": 85.0,
    "disk_threshold": 90.0,
    "check_interval": 30,
    "anomaly_detection": true,
    "log_file": "/var/log/ai-native-linux/kernel_monitor.log"
}
EOF
    
    log "Configuration files created."
}

verify_installation() {
    log "Verifying installation..."
    
    # Check if services are running
    local services=("ai-orchestrator" "quest-log" "kernel-monitor" "self-healing")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if ! systemctl is-active --quiet "$service"; then
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -eq 0 ]; then
        log "All services are running successfully."
    else
        warn "Some services failed to start: ${failed_services[*]}"
        warn "Check logs with: journalctl -u <service-name>"
    fi
    
    # Check if commands are available
    if command -v ai &> /dev/null && command -v ai-terminal &> /dev/null && command -v quest &> /dev/null; then
        log "All commands are available in PATH."
    else
        warn "Some commands may not be available in PATH."
    fi
}

show_usage() {
    log "Installation complete!"
    echo ""
    echo -e "${BLUE}🚀 AI-Native Linux OS is now installed and running!${NC}"
    echo ""
    echo -e "${GREEN}Available Commands:${NC}"
    echo "  ${YELLOW}ai${NC} <query>           - AI Shell Assistant with natural language"
    echo "  ${YELLOW}ai-terminal${NC}          - Launch AI Terminal GUI"
    echo "  ${YELLOW}quest${NC}                - Quest Log viewer for command history"
    echo ""
    echo -e "${GREEN}Services Status:${NC}"
    echo "  ${YELLOW}ai-orchestrator${NC}      - Main AI controller (mixture of agents)"
    echo "  ${YELLOW}quest-log${NC}           - Command logging and analysis"
    echo "  ${YELLOW}kernel-monitor${NC}      - System monitoring with AI insights"
    echo "  ${YELLOW}self-healing${NC}        - Automatic service recovery"
    echo "  ${YELLOW}ollama${NC}              - Local LLM server"
    echo ""
    echo -e "${GREEN}Quick Examples:${NC}"
    echo "  ${BLUE}ai \"list my files\"${NC}"
    echo "  ${BLUE}ai \"check system status\"${NC}"
    echo "  ${BLUE}ai \"install docker\"${NC}"
    echo "  ${BLUE}ai-terminal${NC}          # Launch GUI interface"
    echo "  ${BLUE}quest commands --recent${NC}"
    echo ""
    echo -e "${GREEN}Service Management:${NC}"
    echo "  ${BLUE}systemctl status ai-orchestrator${NC}"
    echo "  ${BLUE}journalctl -u ai-orchestrator -f${NC}"
    echo ""
    echo -e "${GREEN}Configuration:${NC}"
    echo "  ${BLUE}/etc/ai-native-linux/${NC} - Configuration files"
    echo "  ${BLUE}/var/log/ai-native-linux/${NC} - Log files"
    echo ""
    echo -e "${YELLOW}💡 The AI learns from your usage and provides intelligent suggestions!${NC}"
    echo -e "${YELLOW}💡 For GUI interface, run: ai-terminal${NC}"
    echo ""
}

main() {
    log "Starting AI-Native Linux OS one-fell-swoop installation..."
    
    check_requirements
    install_dependencies
    setup_python_env
    install_ollama
    install_components
    create_symlinks
    install_systemd_services
    install_desktop_integration
    create_configuration_files
    verify_installation
    show_usage
    
    log "Installation completed successfully!"
}

# Handle script arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "AI-Native Linux OS - One-Fell-Swoop Installation Script"
    echo ""
    echo "This script installs the complete AI-Native Linux OS system including:"
    echo "  - System dependencies and Python environment"
    echo "  - Ollama LLM server and models"
    echo "  - AI components and mixture of agents"
    echo "  - Command-line tools and GUI interface"
    echo "  - Systemd services for background operation"
    echo "  - Desktop integration and configuration"
    echo ""
    echo "Usage: sudo $0"
    echo ""
    echo "Requirements:"
    echo "  - Debian-based Linux system (Ubuntu, etc.)"
    echo "  - Root privileges (run with sudo)"
    echo "  - Internet connection for downloading dependencies"
    echo ""
    exit 0
fi

# Run main installation
main "$@" 