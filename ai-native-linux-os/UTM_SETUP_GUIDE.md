# UTM Setup Guide: AI-Native Linux OS with Ubuntu Desktop

## Prerequisites
- ✅ UTM installed (already done via Homebrew)
- ⬇️ Ubuntu 24.04 Desktop ARM64 ISO (downloading to ~/Downloads/)
- 💾 At least 8GB RAM available for VM
- 💿 60GB+ free disk space

## Step 1: Create New VM in UTM

1. **Open UTM** from Applications or Launchpad
2. **Click "Create a New Virtual Machine"**
3. **Select "Virtualize"** (for best ARM64 performance)
4. **Choose "Linux"**

## Step 2: Configure VM Settings

### Basic Configuration:
- **Name:** `AI-Native-Linux-OS`
- **ISO Image:** Browse and select `ubuntu-24.04-desktop-arm64.iso` from Downloads
- **Architecture:** ARM64 (should be auto-selected)

### Hardware Configuration:
- **Memory:** 6-8 GB (6144-8192 MB)
  - Minimum: 4GB, Recommended: 6GB+
- **CPU Cores:** 4-6 cores
  - Use half of your Mac's cores for best performance
- **Storage:** 60 GB
  - This gives plenty of space for the OS, your code, and AI datasets

### Display Settings:
- **Display:** VirtIO-GPU
- **Resolution:** 1920x1080 or 1680x1050
- **Enable hardware acceleration:** ✅ ON

### Network:
- **Network Mode:** Shared Network
- **Port Forwarding:** Add these rules:
  - **Web Interface:** Host Port 8080 → Guest Port 8080
  - **SSH:** Host Port 2222 → Guest Port 22

## Step 3: Install Ubuntu Desktop

1. **Start the VM** (click the play button)
2. **Boot from ISO** (should happen automatically)
3. **Select "Try or Install Ubuntu"**
4. **Choose your language** and click "Install Ubuntu"

### Installation Options:
- **Installation type:** Normal installation
- **Download updates while installing:** ✅ ON
- **Install third-party software:** ✅ ON
- **Erase disk and install Ubuntu:** ✅ ON (safe in VM)

### User Setup:
- **Your name:** Your choice
- **Computer name:** `ai-linux-dev`
- **Username:** Your choice (remember this!)
- **Password:** Strong password (remember this!)
- **Log in automatically:** ✅ ON (for convenience)

### Additional Software (select during installation):
- **OpenSSH server:** ✅ ON (for remote access)
- **Docker:** ✅ ON (useful for AI/ML)

## Step 4: Post-Installation Setup

After Ubuntu boots to desktop:

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Essential Tools
```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    htop \
    tree \
    stress-ng \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
```

### 3. Install Development Tools
```bash
# VS Code (optional but recommended)
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=arm64,armhf,amd64 signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
sudo apt update
sudo apt install code -y

# Git configuration
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 5: Install Your AI-Native Linux OS

### 1. Clone Your Repository
```bash
cd ~
git clone https://github.com/Orcadebug/Linux.git
cd Linux/ai-native-linux-os
```

### 2. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Make Scripts Executable
```bash
chmod +x scripts/*.sh
chmod +x quick_test.sh
```

## Step 6: Test Your AI-Native Linux OS

### Quick Test (Recommended First)
```bash
./quick_test.sh
```

### Individual Component Tests

**AI Shell Assistant:**
```bash
python3 src/ai_shell/ai_shell.py "show me system information" --execute
python3 src/ai_shell/ai_shell.py "list files in current directory" --execute
python3 src/ai_shell/ai_shell.py "check cpu usage" --execute
```

**AI/ML Features:**
```bash
python3 src/ai_shell/ai_shell.py "create environment for pytorch" --execute
python3 src/ai_shell/ai_shell.py "teach computer to recognize images" --execute
```

**Web Interface:**
```bash
python3 src/web_interface/app.py
```
Then open Firefox in Ubuntu and go to: `http://localhost:8080`

**System Monitoring:**
```bash
# Terminal 1
python3 src/kernel_monitor/kernel_monitor.py

# Terminal 2 (generate some load)
stress-ng --cpu 2 --timeout 30s
```

**Quest Log System:**
```bash
# Start daemon
python3 src/quest_log/quest_log_daemon.py &

# Generate some activity
ls -la
pwd
whoami

# Check logs
python3 src/quest_log/quest_log_cli.py --recent 10
```

## Step 7: System Integration (Optional)

To install as system services:

```bash
sudo bash scripts/install_system_integration.sh
```

Check if services are running:
```bash
sudo systemctl status ai-shell
sudo systemctl status quest-log
sudo systemctl status kernel-monitor
```

## Step 8: Access from Your Mac

### Web Interface:
Open your Mac browser and go to: `http://localhost:8080`

### SSH Access:
```bash
ssh username@localhost -p 2222
```

### File Transfer:
```bash
# Copy files to VM
scp -P 2222 file.txt username@localhost:~/

# Copy files from VM
scp -P 2222 username@localhost:~/file.txt ./
```

## Performance Tips

### Optimize VM Performance:
1. **Allocate more RAM** if you have it (8GB recommended)
2. **Use SSD storage** for better I/O performance
3. **Close unnecessary applications** on your Mac
4. **Enable hardware acceleration** in UTM display settings

### Ubuntu Desktop Optimization:
```bash
# Reduce visual effects for better performance
gsettings set org.gnome.desktop.interface enable-animations false
gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita'
gsettings set org.gnome.shell.extensions.dash-to-dock extend-height false

# Install GNOME Tweaks for more control
sudo apt install gnome-tweaks -y
```

## Troubleshooting

### VM Won't Boot:
- Ensure you're using ARM64 ISO (not x86_64)
- Check that virtualization is enabled in UTM settings
- Try reducing RAM allocation if your Mac is low on memory

### Slow Performance:
- Increase RAM allocation to 6-8GB
- Enable hardware acceleration
- Close other applications on your Mac
- Use "Shared Network" mode instead of NAT

### Network Issues:
- Check port forwarding settings in UTM
- Ensure Ubuntu firewall allows connections: `sudo ufw allow 8080`
- Try accessing via VM's IP instead of localhost

### Python Package Issues:
```bash
# If pip packages fail to install
python3 -m pip install --upgrade pip setuptools wheel
pip3 install -r requirements.txt --user
```

## What You Can Test

✅ **Fully Functional:**
- All AI Shell Assistant features
- Natural language command translation
- AI/ML environment setup
- Web interface with full GUI
- System monitoring and alerts
- Quest log event tracking
- Self-healing service logic
- Beginner AI tutorials

⚠️ **Limited (VM Environment):**
- GPU acceleration (no physical GPU access)
- Some hardware-specific monitoring
- Deep kernel integration features

## Expected Performance

On M1 Mac with 6-8GB RAM allocated:
- **Ubuntu boot time:** 30-45 seconds
- **AI Shell response:** 100-300ms
- **Web interface:** Smooth and responsive
- **System monitoring:** Real-time updates
- **File operations:** Near-native speed

## Next Steps

Once everything is working:
1. **Explore the web interface** at `http://localhost:8080`
2. **Try the beginner AI tutorials** via natural language commands
3. **Set up your development environment** using AI assistance
4. **Monitor system performance** with the AI kernel monitor
5. **Create AI/ML projects** using the guided templates

🎉 **Congratulations!** You now have a fully functional AI-native Linux OS running on your Mac M1! 