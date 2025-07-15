#!/bin/bash

# AI Terminal GUI Launcher Script
# This script ensures dependencies are installed and launches the AI Terminal GUI

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
AI_TERMINAL_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 AI Terminal GUI Launcher${NC}"
echo -e "${BLUE}=================================${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3 first${NC}"
    exit 1
fi

# Check if tkinter is available
if ! python3 -c "import tkinter" &> /dev/null; then
    echo -e "${RED}❌ tkinter is not available${NC}"
    echo -e "${YELLOW}Please install python3-tk package${NC}"
    echo -e "${YELLOW}Run: sudo apt-get install python3-tk${NC}"
    exit 1
fi

# Check if required Python packages are installed
echo -e "${BLUE}📋 Checking dependencies...${NC}"

# Install missing packages
MISSING_PACKAGES=()

if ! python3 -c "import click" &> /dev/null; then
    MISSING_PACKAGES+=("click")
fi

if ! python3 -c "import requests" &> /dev/null; then
    MISSING_PACKAGES+=("requests")
fi

if ! python3 -c "import psutil" &> /dev/null; then
    MISSING_PACKAGES+=("psutil")
fi

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Installing missing packages: ${MISSING_PACKAGES[*]}${NC}"
    pip3 install --user "${MISSING_PACKAGES[@]}"
fi

# Check if Ollama is available (optional)
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✅ Ollama is available for advanced AI features${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama not found - will use basic AI features${NC}"
    echo -e "${YELLOW}   To install Ollama: curl -fsSL https://ollama.ai/install.sh | sh${NC}"
fi

# Launch the AI Terminal GUI
echo -e "${GREEN}🚀 Launching AI Terminal GUI...${NC}"
cd "$AI_TERMINAL_DIR"

# Run the GUI
python3 ai_terminal_gui.py

echo -e "${GREEN}👋 AI Terminal GUI closed${NC}" 