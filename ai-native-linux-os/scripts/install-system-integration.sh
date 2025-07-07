#!/bin/bash
"""
AI-Native Linux OS - System Integration Script
Installs AI components as native OS services
"""

set -e

# Configuration
AI_OS_DIR="/usr/local/ai-native-os"
SERVICE_DIR="/etc/systemd/system"
BIN_DIR="/usr/local/bin"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$CURRENT_DIR")"

echo "🚀 Installing AI-Native Linux OS components..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Create system directories
echo "📁 Creating system directories..."
mkdir -p "$AI_OS_DIR"/{bin,lib,share,models,logs}
mkdir -p "$AI_OS_DIR/lib/python"
mkdir -p "$AI_OS_DIR/share/web_interface"

# Copy application files
echo "📋 Copying application files..."
cp -r "$PROJECT_ROOT/src/"* "$AI_OS_DIR/lib/"
cp -r "$PROJECT_ROOT/src/web_interface" "$AI_OS_DIR/share/"
cp "$PROJECT_ROOT/requirements.txt" "$AI_OS_DIR/"

# Create executable wrapper scripts
echo "🔧 Creating system executables..."

# AI Shell wrapper
cat > "$AI_OS_DIR/bin/ai-shell" << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/local/ai-native-os/lib:$PYTHONPATH"
cd /usr/local/ai-native-os
python3 lib/ai_shell/ai_shell.py "$@"
EOF

# Quest Log daemon wrapper  
cat > "$AI_OS_DIR/bin/quest-log-daemon" << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/local/ai-native-os/lib:$PYTHONPATH"
cd /usr/local/ai-native-os
python3 lib/quest_log/quest_log_daemon.py
EOF

# Kernel Monitor wrapper
cat > "$AI_OS_DIR/bin/ai-monitor" << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/local/ai-native-os/lib:$PYTHONPATH"
cd /usr/local/ai-native-os
python3 lib/kernel_monitor/kernel_monitor.py
EOF

# Self-Healing Service wrapper
cat > "$AI_OS_DIR/bin/self-healing" << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/local/ai-native-os/lib:$PYTHONPATH"
cd /usr/local/ai-native-os
python3 lib/self_healing/self_healing.py
EOF

# Web Interface wrapper
cat > "$AI_OS_DIR/bin/ai-web-interface" << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/local/ai-native-os/lib:$PYTHONPATH"
cd /usr/local/ai-native-os/share/web_interface
python3 app.py
EOF

# Make scripts executable
chmod +x "$AI_OS_DIR/bin/"*

# Create symlinks in system PATH
echo "🔗 Creating system symlinks..."
ln -sf "$AI_OS_DIR/bin/ai-shell" "$BIN_DIR/ai-shell"
ln -sf "$AI_OS_DIR/bin/quest-log-daemon" "$BIN_DIR/quest-log-daemon"
ln -sf "$AI_OS_DIR/bin/ai-monitor" "$BIN_DIR/ai-monitor"
ln -sf "$AI_OS_DIR/bin/self-healing" "$BIN_DIR/self-healing"
ln -sf "$AI_OS_DIR/bin/ai-web-interface" "$BIN_DIR/ai-web-interface"

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r "$AI_OS_DIR/requirements.txt"

# Download initial AI models
echo "🧠 Downloading initial AI models..."
mkdir -p "$AI_OS_DIR/models"
python3 -c "
import os
os.chdir('$AI_OS_DIR/models')

# Download lightweight models for offline operation
try:
    from transformers import pipeline
    print('📥 Downloading sentiment analysis model...')
    sentiment = pipeline('sentiment-analysis')
    print('📥 Downloading text generation model...')
    generator = pipeline('text-generation', model='gpt2')
    print('✅ Base models downloaded successfully')
except Exception as e:
    print(f'⚠️  Could not download models: {e}')
    print('Models will be downloaded on first use')
"

# Create systemd services
echo "⚙️ Creating systemd services..."

# Quest Log Daemon Service
cat > "$SERVICE_DIR/ai-quest-log.service" << EOF
[Unit]
Description=AI-Native OS Quest Log Daemon
Documentation=https://github.com/Orcadebug/Linux
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=root
ExecStart=$AI_OS_DIR/bin/quest-log-daemon
WorkingDirectory=$AI_OS_DIR
Environment=PYTHONPATH=$AI_OS_DIR/lib

[Install]
WantedBy=multi-user.target
EOF

# Kernel Monitor Service
cat > "$SERVICE_DIR/ai-monitor.service" << EOF
[Unit]
Description=AI-Native OS Kernel Monitor
Documentation=https://github.com/Orcadebug/Linux
After=network.target ai-quest-log.service
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=root
ExecStart=$AI_OS_DIR/bin/ai-monitor
WorkingDirectory=$AI_OS_DIR
Environment=PYTHONPATH=$AI_OS_DIR/lib

[Install]
WantedBy=multi-user.target
EOF

# Self-Healing Service
cat > "$SERVICE_DIR/ai-self-healing.service" << EOF
[Unit]
Description=AI-Native OS Self-Healing Service
Documentation=https://github.com/Orcadebug/Linux
After=network.target ai-quest-log.service
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=root
ExecStart=$AI_OS_DIR/bin/self-healing
WorkingDirectory=$AI_OS_DIR
Environment=PYTHONPATH=$AI_OS_DIR/lib

[Install]
WantedBy=multi-user.target
EOF

# Web Interface Service (Optional)
cat > "$SERVICE_DIR/ai-web-interface.service" << EOF
[Unit]
Description=AI-Native OS Web Interface
Documentation=https://github.com/Orcadebug/Linux
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=www-data
ExecStart=$AI_OS_DIR/bin/ai-web-interface
WorkingDirectory=$AI_OS_DIR/share/web_interface
Environment=PYTHONPATH=$AI_OS_DIR/lib

[Install]
WantedBy=multi-user.target
EOF

# Add AI shell to available shells
echo "🐚 Registering AI shell..."
if ! grep -q "$AI_OS_DIR/bin/ai-shell" /etc/shells; then
    echo "$AI_OS_DIR/bin/ai-shell" >> /etc/shells
fi

# Enable and start services
echo "🔄 Enabling and starting services..."
systemctl daemon-reload
systemctl enable ai-quest-log.service
systemctl enable ai-monitor.service  
systemctl enable ai-self-healing.service
systemctl enable ai-web-interface.service

systemctl start ai-quest-log.service
systemctl start ai-monitor.service
systemctl start ai-self-healing.service
systemctl start ai-web-interface.service

# Create AI user configuration
echo "👤 Setting up AI user configuration..."
mkdir -p /etc/ai-native-os
cat > /etc/ai-native-os/config.yaml << EOF
# AI-Native OS Configuration
version: "1.0"

ai_shell:
  default_model: "local"
  fallback_to_cloud: false
  history_size: 10000

quest_log:
  log_level: "INFO"
  retention_days: 30
  enable_ai_analysis: true

kernel_monitor:
  check_interval: 5
  alert_threshold: 80
  enable_gpu_monitoring: true

self_healing:
  auto_restart: true
  max_restart_attempts: 3
  cooldown_period: 300

web_interface:
  host: "0.0.0.0"
  port: 8080
  enable_tutorial: true
EOF

# Create log rotation
cat > /etc/logrotate.d/ai-native-os << EOF
$AI_OS_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# Final status check
echo "🔍 Checking service status..."
sleep 2
systemctl --no-pager status ai-quest-log.service
systemctl --no-pager status ai-monitor.service
systemctl --no-pager status ai-self-healing.service
systemctl --no-pager status ai-web-interface.service

echo ""
echo "✅ AI-Native Linux OS installation complete!"
echo ""
echo "🎯 Quick Start:"
echo "   • AI Shell: ai-shell"
echo "   • Web Interface: http://localhost:8080"
echo "   • View logs: journalctl -u ai-quest-log.service"
echo "   • Check status: systemctl status ai-*"
echo ""
echo "🔧 Configuration:"
echo "   • System config: /etc/ai-native-os/config.yaml"
echo "   • AI models: $AI_OS_DIR/models/"
echo "   • Logs: $AI_OS_DIR/logs/"
echo ""
echo "🚀 To make AI shell default for a user:"
echo "   sudo chsh -s $AI_OS_DIR/bin/ai-shell username"
echo "" 