# AI-Native Linux OS - Quick Start Guide

## Overview

AI-Native Linux OS is a demo-quality Linux distribution featuring AI-powered system management, natural language shell assistance, comprehensive system logging, and automated service recovery.

## Quick Demo

### 1. Building the OS

```bash
# Prerequisites (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y debootstrap squashfs-tools xorriso isolinux syslinux-utils

# Build the ISO
sudo ./build/build_iso.sh
```

### 2. Installing on Existing System

```bash
# Install AI components on existing Linux system
sudo ./scripts/install.sh
```

### 3. Using AI Features

```bash
# AI Shell Assistant
ai "list files in current directory"
ai "show memory usage"
ai "find all python files"

# Quest Log (System Activity Viewer)
quest commands --limit 20
quest events --type high_load
quest search "python"
quest stats

# Quick aliases
qlog        # Recent commands
qsearch     # Search logs
```

## Core Features

### 1. AI Shell Assistant
- Natural language to shell command translation
- Context-aware suggestions
- Safety checks for dangerous commands
- Command explanations

**Example Usage:**
```bash
ai "show disk space"           # → df -h
ai "list running processes"    # → ps aux  
ai "create directory backup"   # → mkdir -p backup
ai "find large files"          # → find . -type f -size +100M
```

### 2. Quest Log System
- Automatic logging of all shell commands
- System event tracking (high CPU, low disk, etc.)
- Searchable command history
- Statistics and analysis

**Example Usage:**
```bash
quest commands --user john --limit 10
quest events --type memory_high --since "1 hour ago"
quest search "git commit"
quest stats
```

### 3. AI Kernel Monitor
- Real-time system monitoring
- Anomaly detection using machine learning
- Intelligent alerting with suggestions
- Performance threshold monitoring

**Monitored Metrics:**
- CPU usage (default threshold: 80%)
- Memory usage (default threshold: 85%)
- Disk usage (default threshold: 90%)
- System load average
- Network activity

### 4. Self-Healing Service
- Automatic service restart on failure
- Process monitoring and recovery
- Configurable restart policies
- Comprehensive logging of healing actions

**Monitored Services:**
- SSH daemon
- Quest Log daemon
- Kernel Monitor
- Custom user processes

## System Requirements

### Minimum Requirements
- 2GB RAM
- 10GB disk space
- x86_64 processor
- Network connectivity (for AI features)

### Recommended Requirements
- 4GB RAM
- 20GB disk space
- Multi-core processor
- SSD storage

## Installation Methods

### Method 1: Live ISO
1. Download the ISO from releases
2. Create bootable USB: `dd if=ai-native-linux-os.iso of=/dev/sdX bs=4M`
3. Boot from USB
4. Login as `ai-user` (no password)

### Method 2: Install on Existing System
1. Clone the repository
2. Run installation script: `sudo ./scripts/install.sh`
3. Reboot or source `/etc/profile.d/ai-native-linux.sh`

### Method 3: VM Installation
1. Create new VM with 4GB RAM, 20GB disk
2. Boot from AI-Native Linux ISO
3. Follow installation prompts

## Configuration

### AI Shell Assistant
Edit `/etc/ai-native-linux/ai_shell.json`:
```json
{
    "llm_provider": "local",
    "max_history": 100,
    "safety_check": true,
    "dangerous_commands": ["rm -rf", "dd if=", "mkfs"]
}
```

### Kernel Monitor
Edit `/etc/ai-native-linux/kernel_monitor.json`:
```json
{
    "cpu_threshold": 80.0,
    "memory_threshold": 85.0,
    "disk_threshold": 90.0,
    "check_interval": 5,
    "anomaly_detection": true
}
```

### Self-Healing Service
Edit `/etc/ai-native-linux/self_healing.json`:
```json
{
    "services": [
        {
            "name": "sshd",
            "command": "systemctl start sshd",
            "check_command": "systemctl is-active sshd",
            "critical": true,
            "max_restarts": 3,
            "restart_delay": 30
        }
    ],
    "check_interval": 30
}
```

## Testing

### Run Full Test Suite
```bash
./tests/run_tests.sh
```

### Run Specific Tests
```bash
./tests/run_tests.sh --unit           # Unit tests only
./tests/run_tests.sh --functional     # Functional tests only
./tests/run_tests.sh --performance    # Performance tests only
```

### Manual Testing
```bash
# Test AI Shell Assistant
ai "list files" --explain

# Test Quest Log
quest stats

# Test service status
systemctl status quest-log-daemon
systemctl status kernel-monitor
systemctl status self-healing-service
```

## Troubleshooting

### Common Issues

1. **AI Shell Assistant not responding**
   - Check if service is running: `systemctl status quest-log-daemon`
   - Check logs: `journalctl -u quest-log-daemon`

2. **High resource usage**
   - Check AI monitoring: `quest events --type high_load`
   - Adjust thresholds in `/etc/ai-native-linux/kernel_monitor.json`

3. **Services not starting**
   - Check systemd status: `systemctl status <service-name>`
   - Check permissions: `ls -la /opt/ai-native-linux/`

### Log Locations
- Quest Log: SQLite database at `~/.quest_log.db`
- Kernel Monitor: `/var/log/kernel_monitor.log`
- Self-Healing: `/var/log/self_healing.log`
- System logs: `journalctl -u <service-name>`

## Development

### Building from Source
```bash
git clone <repository>
cd ai-native-linux-os
pip3 install -r requirements.txt
./tests/run_tests.sh
sudo ./build/build_iso.sh
```

### Contributing
1. Fork the repository
2. Create feature branch
3. Run tests: `./tests/run_tests.sh`
4. Submit pull request

## Performance Tuning

### Optimize for Low Resource Systems
```json
// kernel_monitor.json
{
    "check_interval": 30,
    "anomaly_detection": false,
    "max_history": 100
}
```

### Optimize for High Performance Systems
```json
// kernel_monitor.json
{
    "check_interval": 1,
    "anomaly_detection": true,
    "max_history": 10000
}
```

## Next Steps

1. **Explore AI Features**: Try various natural language queries with the AI shell
2. **Monitor System**: Watch the Quest Log fill up with system activity
3. **Test Self-Healing**: Stop a service and watch it automatically restart
4. **Customize Configuration**: Adjust thresholds and monitoring intervals
5. **Extend Functionality**: Add custom services to monitor and heal

## Support

- GitHub Issues: Report bugs and request features
- Documentation: Check `/opt/ai-native-linux/docs/`
- Logs: Use `journalctl` and Quest Log for troubleshooting

---

**Note**: This is a demonstration/MVP version. Not recommended for production use.