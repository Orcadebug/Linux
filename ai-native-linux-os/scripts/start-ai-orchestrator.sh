#!/bin/bash
"""
AI-Native Linux OS - Orchestrator Startup Script
"""

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AI_ORCHESTRATOR_PATH="$PROJECT_ROOT/src/ai_orchestrator"
LOG_FILE="/var/log/ai-orchestrator.log"
PID_FILE="/var/run/ai-orchestrator.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# Check if running as root for system-wide installation
check_permissions() {
    if [[ $EUID -eq 0 ]] && [[ "$1" != "--system" ]]; then
        warning "Running as root without --system flag. Consider using regular user permissions."
    fi
    
    if [[ "$1" == "--system" ]] && [[ $EUID -ne 0 ]]; then
        error "System installation requires root privileges. Use sudo."
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi
    
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version < 3.7" | bc -l) -eq 1 ]]; then
        error "Python 3.7+ is required. Found Python $python_version"
        exit 1
    fi
    
    success "Python $python_version found"
    
    # Check virtual environment
    if [[ ! -d "$PROJECT_ROOT/venv" ]] && [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
        log "Creating Python virtual environment..."
        python3 -m venv "$PROJECT_ROOT/venv"
        source "$PROJECT_ROOT/venv/bin/activate"
        
        # Install requirements
        if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
            log "Installing Python dependencies..."
            pip install --upgrade pip
            pip install -r "$PROJECT_ROOT/requirements.txt"
        fi
    else
        log "Virtual environment found"
    fi
    
    # Check Ollama
    if command -v ollama &> /dev/null; then
        success "Ollama found"
        
        # Check if Ollama is running
        if ! pgrep -f ollama &> /dev/null; then
            log "Starting Ollama service..."
            ollama serve &
            sleep 3
        fi
        
        # Check for a lightweight model
        if ! ollama list | grep -q "phi3"; then
            log "Downloading lightweight AI model (phi3:mini)..."
            ollama pull phi3:mini
        fi
    else
        warning "Ollama not found. Some AI features may not work. Install from https://ollama.ai"
    fi
    
    # Check system tools
    local tools=("ps" "kill" "pgrep" "pkill" "systemctl")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            warning "$tool not found. Some features may not work."
        fi
    done
}

# Check if orchestrator is already running
check_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"
        fi
    fi
    return 1  # Not running
}

# Start the AI orchestrator
start_orchestrator() {
    local mode="${1:-daemon}"
    
    if check_running; then
        warning "AI Orchestrator is already running (PID: $(cat $PID_FILE))"
        return 0
    fi
    
    log "Starting AI-Native Linux OS Orchestrator..."
    
    # Change to project directory
    cd "$PROJECT_ROOT" || exit 1
    
    # Activate virtual environment
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    elif [[ -d ".venv" ]]; then
        source .venv/bin/activate
    fi
    
    # Export necessary environment variables
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    export AI_ORCHESTRATOR_LOG_LEVEL="${AI_ORCHESTRATOR_LOG_LEVEL:-INFO}"
    export AI_ORCHESTRATOR_CONFIG="${AI_ORCHESTRATOR_CONFIG:-$PROJECT_ROOT/config/orchestrator.json}"
    
    if [[ "$mode" == "daemon" ]]; then
        # Start as daemon
        nohup python3 -m ai_orchestrator.main_ai_controller > "$LOG_FILE" 2>&1 &
        local pid=$!
        echo "$pid" > "$PID_FILE"
        
        # Wait a moment and check if it started successfully
        sleep 2
        if ps -p "$pid" > /dev/null 2>&1; then
            success "AI Orchestrator started successfully (PID: $pid)"
        else
            error "Failed to start AI Orchestrator"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        # Start in foreground
        log "Starting in foreground mode (Ctrl+C to stop)..."
        python3 -m ai_orchestrator.main_ai_controller
    fi
}

# Stop the AI orchestrator
stop_orchestrator() {
    if ! check_running; then
        warning "AI Orchestrator is not running"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    log "Stopping AI Orchestrator (PID: $pid)..."
    
    # Send SIGTERM first
    kill -TERM "$pid" 2>/dev/null
    
    # Wait for graceful shutdown
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 10 ]]; do
        sleep 1
        ((count++))
    done
    
    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        warning "Graceful shutdown failed, forcing termination..."
        kill -KILL "$pid" 2>/dev/null
        sleep 1
    fi
    
    # Clean up
    rm -f "$PID_FILE"
    
    if ! ps -p "$pid" > /dev/null 2>&1; then
        success "AI Orchestrator stopped successfully"
    else
        error "Failed to stop AI Orchestrator"
        return 1
    fi
}

# Restart the orchestrator
restart_orchestrator() {
    log "Restarting AI Orchestrator..."
    stop_orchestrator
    sleep 2
    start_orchestrator "$1"
}

# Show status
show_status() {
    echo "=== AI-Native Linux OS Orchestrator Status ==="
    echo
    
    if check_running; then
        local pid=$(cat "$PID_FILE")
        success "Status: RUNNING (PID: $pid)"
        
        # Show process details
        if command -v ps &> /dev/null; then
            echo "Process details:"
            ps -p "$pid" -o pid,ppid,cmd,etime,%cpu,%mem
        fi
        
        # Show recent log entries
        echo
        echo "Recent log entries:"
        if [[ -f "$LOG_FILE" ]]; then
            tail -10 "$LOG_FILE"
        else
            echo "No log file found"
        fi
    else
        warning "Status: NOT RUNNING"
    fi
    
    echo
    echo "Configuration:"
    echo "  Project root: $PROJECT_ROOT"
    echo "  Log file: $LOG_FILE"
    echo "  PID file: $PID_FILE"
    echo "  Python path: $PYTHONPATH"
    
    # Check dependencies status
    echo
    echo "Dependencies:"
    if command -v python3 &> /dev/null; then
        echo "  ✓ Python: $(python3 --version)"
    else
        echo "  ✗ Python: Not found"
    fi
    
    if command -v ollama &> /dev/null; then
        echo "  ✓ Ollama: $(ollama --version 2>/dev/null || echo 'Found')"
        if pgrep -f ollama &> /dev/null; then
            echo "    ✓ Ollama service: Running"
        else
            echo "    ✗ Ollama service: Not running"
        fi
    else
        echo "  ✗ Ollama: Not found"
    fi
}

# Show logs
show_logs() {
    local lines="${1:-50}"
    
    if [[ -f "$LOG_FILE" ]]; then
        echo "=== AI Orchestrator Logs (last $lines lines) ==="
        tail -"$lines" "$LOG_FILE"
    else
        warning "Log file not found: $LOG_FILE"
    fi
}

# Install system service
install_service() {
    if [[ $EUID -ne 0 ]]; then
        error "Installing system service requires root privileges"
        exit 1
    fi
    
    log "Installing AI Orchestrator as system service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/ai-orchestrator.service << EOF
[Unit]
Description=AI-Native Linux OS Orchestrator
After=network.target
Wants=network.target

[Service]
Type=forking
User=root
Group=root
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT/src
Environment=AI_ORCHESTRATOR_LOG_LEVEL=INFO
ExecStart=$PROJECT_ROOT/scripts/start-ai-orchestrator.sh start --daemon
ExecStop=$PROJECT_ROOT/scripts/start-ai-orchestrator.sh stop
ExecReload=$PROJECT_ROOT/scripts/start-ai-orchestrator.sh restart --daemon
PIDFile=$PID_FILE
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable ai-orchestrator.service
    
    success "System service installed. Use 'systemctl start ai-orchestrator' to start"
}

# Uninstall system service
uninstall_service() {
    if [[ $EUID -ne 0 ]]; then
        error "Uninstalling system service requires root privileges"
        exit 1
    fi
    
    log "Uninstalling AI Orchestrator system service..."
    
    systemctl stop ai-orchestrator.service 2>/dev/null
    systemctl disable ai-orchestrator.service 2>/dev/null
    rm -f /etc/systemd/system/ai-orchestrator.service
    systemctl daemon-reload
    
    success "System service uninstalled"
}

# Show help
show_help() {
    cat << EOF
AI-Native Linux OS Orchestrator Control Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    start [--foreground|--daemon]  Start the orchestrator (default: daemon)
    stop                          Stop the orchestrator
    restart [--foreground|--daemon] Restart the orchestrator
    status                        Show current status
    logs [LINES]                 Show recent log entries (default: 50 lines)
    
System Commands (require root):
    install-service              Install as systemd service
    uninstall-service           Remove systemd service
    
Options:
    --system                     System-wide installation
    --foreground                 Run in foreground (for debugging)
    --daemon                     Run as background daemon (default)
    --help, -h                   Show this help message

Examples:
    $0 start                     # Start as daemon
    $0 start --foreground        # Start in foreground for debugging
    $0 restart                   # Restart the service
    $0 logs 100                  # Show last 100 log lines
    sudo $0 install-service      # Install system service

Log file: $LOG_FILE
PID file: $PID_FILE
EOF
}

# Main script logic
main() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Check permissions
    check_permissions "$@"
    
    case "${1:-status}" in
        start)
            check_dependencies
            if [[ "$2" == "--foreground" ]]; then
                start_orchestrator "foreground"
            else
                start_orchestrator "daemon"
            fi
            ;;
        stop)
            stop_orchestrator
            ;;
        restart)
            check_dependencies
            if [[ "$2" == "--foreground" ]]; then
                restart_orchestrator "foreground"
            else
                restart_orchestrator "daemon"
            fi
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-50}"
            ;;
        install-service)
            check_dependencies
            install_service
            ;;
        uninstall-service)
            uninstall_service
            ;;
        --help|-h|help)
            show_help
            ;;
        *)
            error "Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 