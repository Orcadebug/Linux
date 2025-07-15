#!/bin/bash

# AI Terminal GUI System Installation Script
# This script installs the AI Terminal GUI system-wide

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 AI Terminal GUI System Installer${NC}"
echo -e "${BLUE}====================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ This script must be run as root${NC}"
    echo -e "${YELLOW}Please run: sudo $0${NC}"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}📂 Project root: $PROJECT_ROOT${NC}"

# Create directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p /opt/ai-terminal
mkdir -p /usr/local/bin

# Copy AI Terminal files
echo -e "${BLUE}📋 Copying AI Terminal files...${NC}"
cp -r "$PROJECT_ROOT/src/ai_shell/"* /opt/ai-terminal/
chmod +x /opt/ai-terminal/launch_ai_terminal.sh

# Create system-wide launcher script
echo -e "${BLUE}🚀 Creating launcher script...${NC}"
cat > /usr/local/bin/ai-terminal << 'EOF'
#!/bin/bash
# AI Terminal GUI System Launcher
cd /opt/ai-terminal
exec ./launch_ai_terminal.sh "$@"
EOF

chmod +x /usr/local/bin/ai-terminal

# Install desktop entry
echo -e "${BLUE}🖥️  Installing desktop entry...${NC}"
cp "$PROJECT_ROOT/ai-terminal.desktop" /usr/share/applications/
chmod 644 /usr/share/applications/ai-terminal.desktop

# Update desktop database
echo -e "${BLUE}🔄 Updating desktop database...${NC}"
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications/
fi

# Install system dependencies
echo -e "${BLUE}📦 Installing system dependencies...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-tk

# Install Python dependencies
echo -e "${BLUE}🐍 Installing Python dependencies...${NC}"
pip3 install click requests psutil

# Optional: Install Ollama for advanced AI features
echo -e "${YELLOW}⚠️  Optional: Install Ollama for advanced AI features${NC}"
read -p "Do you want to install Ollama? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}📥 Installing Ollama...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
    echo -e "${GREEN}✅ Ollama installed${NC}"
    echo -e "${YELLOW}💡 After installation, run: ollama pull phi3${NC}"
fi

# Create application menu entry
echo -e "${BLUE}📋 Creating application menu entry...${NC}"

# Set permissions
chown -R root:root /opt/ai-terminal
chmod -R 755 /opt/ai-terminal

echo -e "${GREEN}✅ Installation complete!${NC}"
echo -e "${GREEN}🎉 You can now launch AI Terminal from:${NC}"
echo -e "${GREEN}   • Applications menu -> System -> AI Terminal${NC}"
echo -e "${GREEN}   • Run 'ai-terminal' from any terminal${NC}"
echo -e "${GREEN}   • Alt+F2 -> 'ai-terminal'${NC}"
echo
echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "${YELLOW}   • The AI Terminal learns from your usage${NC}"
echo -e "${YELLOW}   • Try saying 'show me my files' or 'create a folder'${NC}"
echo -e "${YELLOW}   • All conversations are saved locally${NC}"
echo
echo -e "${BLUE}🚀 Launch AI Terminal now? (Y/n)${NC}"
read -p "> " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${GREEN}🚀 Launching AI Terminal...${NC}"
    sudo -u "$SUDO_USER" ai-terminal &
fi 