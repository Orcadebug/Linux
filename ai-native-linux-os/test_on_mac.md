# Testing AI-Native Linux OS on Mac M1

## Quick Setup Guide for UTM

### Step 1: UTM VM Setup

1. **Open UTM** (already installed via Homebrew)
2. **Create New VM:**
   - Click "Create a New Virtual Machine"
   - Select "Virtualize" (for ARM64 performance)
   - Choose "Linux"

3. **VM Configuration:**
   - **ISO Image:** Use `ubuntu-24.04-live-server-arm64.iso` (downloading)
   - **Memory:** 4-8 GB RAM (recommended: 6GB)
   - **CPU Cores:** 4-6 cores
   - **Storage:** 40-60 GB disk space
   - **Display:** Enable hardware acceleration

### Step 2: Ubuntu Installation

1. **Boot from ISO** and install Ubuntu Server
2. **During installation:**
   - Enable SSH server
   - Install Docker (optional but recommended)
   - Create user account

3. **Post-installation:**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python and pip
   sudo apt install python3 python3-pip python3-venv git -y
   
   # Install system monitoring tools
   sudo apt install htop nvtop tree curl wget -y
   ```

### Step 3: Install Your AI-Native Linux OS

1. **Clone your repository:**
   ```bash
   git clone https://github.com/Orcadebug/Linux.git
   cd Linux/ai-native-linux-os
   ```

2. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Test individual components:**

   **AI Shell Assistant:**
   ```bash
   python3 src/ai_shell/ai_shell.py "show me system information"
   python3 src/ai_shell/ai_shell.py "list files in current directory"
   python3 src/ai_shell/ai_shell.py "check cpu usage"
   ```

   **Kernel Monitor:**
   ```bash
   python3 src/kernel_monitor/kernel_monitor.py
   # Let it run for a few minutes to see system monitoring
   ```

   **Quest Log:**
   ```bash
   python3 src/quest_log/quest_log_daemon.py &
   python3 src/quest_log/quest_log_cli.py --recent 10
   ```

   **Web Interface:**
   ```bash
   python3 src/web_interface/app.py
   # Access via http://VM_IP:8080 from your Mac browser
   ```

### Step 4: Advanced Testing

**Test AI/ML Features:**
```bash
# Test GPU detection (will show no GPU in VM)
python3 src/ai_shell/ai_shell.py "gpu status"

# Test environment setup
python3 src/ai_shell/ai_shell.py "create environment for pytorch"

# Test beginner AI commands
python3 src/ai_shell/ai_shell.py "teach computer to recognize images"
```

**Test System Integration:**
```bash
# Run the system integration script
sudo bash scripts/install_system_integration.sh

# Check if services are running
sudo systemctl status ai-shell
sudo systemctl status quest-log
sudo systemctl status kernel-monitor
```

### Step 5: Performance Testing

**Monitor Resource Usage:**
```bash
# In one terminal
htop

# In another terminal
python3 src/kernel_monitor/kernel_monitor.py

# Test load
stress-ng --cpu 4 --timeout 60s
```

**Test All Components Together:**
```bash
# Start all services
./scripts/start_all_services.sh

# Run integration tests
cd tests
bash run_tests.sh
```

## Alternative Options

### Option 2: Docker Testing (Simpler)

If you want to test just the Python components without full OS integration:

```bash
# On your Mac
cd ai-native-linux-os

# Build Docker container
docker build -t ai-native-linux .

# Run container
docker run -it --rm -v $(pwd):/app ai-native-linux bash

# Inside container, test components
python3 src/ai_shell/ai_shell.py "list files"
```

### Option 3: Lima (Lightweight)

For lighter testing:

```bash
# Install Lima
brew install lima

# Create Ubuntu VM
limactl start --name=ai-linux template://ubuntu

# SSH into VM
lima ai-linux

# Clone and test your OS
git clone https://github.com/Orcadebug/Linux.git
cd Linux/ai-native-linux-os
pip3 install -r requirements.txt
python3 src/ai_shell/ai_shell.py "hello world"
```

## What You Can Test

✅ **Fully Functional:**
- AI Shell Assistant natural language translation
- Quest Log system event tracking
- Kernel Monitor system metrics
- Web interface for beginners
- Self-healing service logic
- All Python-based features

⚠️ **Limited in VM:**
- GPU detection (no physical GPU access)
- Some hardware-specific monitoring
- Deep kernel integration

🚫 **Not Available:**
- Real GPU/CUDA features (unless you have eGPU)
- Some low-level hardware monitoring

## Expected Performance

On M1 Mac with UTM:
- **Boot time:** 30-60 seconds
- **AI Shell response:** 100-500ms
- **System monitoring:** Real-time
- **Web interface:** Smooth and responsive

## Troubleshooting

**If VM is slow:**
- Increase RAM allocation to 6-8GB
- Enable hardware acceleration in UTM
- Use ARM64 Ubuntu (not x86_64)

**If networking issues:**
- Use "Shared Network" mode in UTM
- Forward port 8080 for web interface

**If Python errors:**
- Make sure you're using Python 3.8+
- Install missing packages: `pip3 install <package>` 