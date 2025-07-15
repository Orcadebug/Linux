# 🤖 AI Terminal GUI - Talk to Your Computer

A minimalist, beginner-friendly GUI application that lets you control your computer using natural language. Instead of memorizing complex commands, just tell your computer what you want to do!

## ✨ Features

- **Natural Language Interface**: Type requests like "show me my files" or "create a folder called Photos"
- **Conversational**: Maintains context across multiple requests
- **Beginner-Friendly**: No technical jargon - designed for anyone to use
- **AI-Powered**: Uses local LLMs (like Ollama) for advanced understanding
- **Safe**: Always asks before executing potentially dangerous commands
- **Persistent Memory**: Remembers your conversations and learns from your usage
- **Visual Feedback**: Clear explanations of what each command does

## 🚀 Quick Start

### 🎯 One-Line Install (Recommended)
```bash
curl -sSL https://raw.githubusercontent.com/Orcadebug/Linux/main/ai-native-linux-os/install.sh | sudo bash
```

This installs the complete AI-Native Linux OS including the AI Terminal GUI, background services, and command-line tools. After installation:

```bash
ai-terminal                  # Launch GUI
ai "show me my files"        # Use CLI
```

### Option 1: System-Wide Installation (Alternative)
```bash
# Install system-wide (requires sudo)
sudo ./scripts/install-ai-terminal.sh

# Then launch from Applications menu or run:
ai-terminal
```

### Option 2: Direct Launch (Development)
```bash
# Install dependencies first
pip3 install -r requirements.txt

# Launch directly
./src/ai_shell/launch_ai_terminal.sh
```

## 💬 How to Use

1. **Launch** the AI Terminal from your Applications menu or run `ai-terminal`
2. **Type naturally** - just describe what you want to do:
   - "Show me my files"
   - "What's taking up disk space?"
   - "Create a folder called Documents"
   - "Find files with .txt extension"
   - "Install Python packages"
   - "Check my system memory"
3. **Review** the suggested command and explanation
4. **Approve** or decline the command execution
5. **Continue** the conversation - the AI remembers context!

## 🎯 Example Conversations

### File Management
```
You: "Show me my files"
AI: I can help you with that! Here's what I'll do:
    Command: ls -la
    Explanation: List all files with detailed information
    
You: "Create a folder for my photos"
AI: I'll create a directory for you:
    Command: mkdir -p Photos
    Explanation: Create directory named Photos
```

### System Information
```
You: "How much disk space do I have?"
AI: Let me check your disk usage:
    Command: df -h
    Explanation: Show disk usage in human-readable format
    
You: "What's using my memory?"
AI: I'll show you memory usage:
    Command: free -h
    Explanation: Show memory usage in human-readable format
```

### AI/ML Projects
```
You: "Help me learn AI"
AI: I'll set up an AI learning environment:
    Command: python3 -m venv ai_env && source ai_env/bin/activate
    Explanation: Create and activate a Python virtual environment for AI
    
You: "Setup PyTorch"
AI: I'll install PyTorch for you:
    Command: pip3 install torch torchvision torchaudio
    Explanation: Install PyTorch machine learning framework
```

## 🧠 AI Features

### Local LLM Support
- **Ollama Integration**: Uses local models like Phi-3, Llama, or Mistral
- **Hardware-Aware**: Automatically selects the best model for your system
- **Privacy-First**: All processing happens locally on your machine
- **Fallback**: Uses rule-based translation if LLM is unavailable

### Smart Model Selection
- **16GB+ RAM**: Uses Llama3 for advanced understanding
- **8GB+ RAM**: Uses Phi-3 for balanced performance
- **4GB+ RAM**: Uses TinyLLM for basic functionality

## 🔧 Technical Details

### Requirements
- **Python 3.7+**
- **tkinter** (usually included with Python)
- **Dependencies**: click, requests, psutil, ollama (optional)

### File Locations
- **Conversation History**: `~/.ai_shell_conversation.json`
- **Command History**: `~/.ai_shell_history`
- **Installation**: `/opt/ai-terminal/` (system-wide)

### Safety Features
- **Dangerous Command Detection**: Warns before executing risky commands
- **Confirmation Dialogs**: Always asks before executing commands
- **Timeout Protection**: Commands timeout after 30 seconds
- **Error Handling**: Graceful error reporting and recovery

## 🛠️ Development

### Architecture
- **Backend**: `ai_shell.py` - Core AI assistant logic
- **Frontend**: `ai_terminal_gui.py` - Tkinter GUI interface
- **Launcher**: `launch_ai_terminal.sh` - Dependency management and startup
- **Installer**: `install-ai-terminal.sh` - System-wide installation

### Extending the AI Terminal
The AI Terminal is designed to be extensible:
- **Custom Commands**: Add new translation rules in `translate_natural_language()`
- **New AI Models**: Extend `select_llm_model()` for different model providers
- **UI Themes**: Modify colors and styling in `setup_gui()`
- **Integrations**: Connect to other OS modules (quest log, kernel monitor, etc.)

## 🤝 Integration with AI-Native OS

The AI Terminal is part of the larger AI-Native Linux OS project:
- **Quest Log**: Tracks and analyzes your activities
- **Kernel Monitor**: AI-powered system monitoring
- **Self-Healing**: Automated problem resolution
- **Web Interface**: Beginner-friendly web dashboard

## 📝 Tips for Best Results

1. **Be Specific**: "Create a folder called Photos" vs "make folder"
2. **Use Context**: The AI remembers previous commands in the conversation
3. **Ask Questions**: "What does this command do?" or "Is this safe?"
4. **Natural Language**: Type like you're talking to a friend
5. **Experiment**: Try different ways of asking for the same thing

## 🐛 Troubleshooting

### Common Issues
- **tkinter not found**: Install with `sudo apt-get install python3-tk`
- **Ollama not working**: Install with `curl -fsSL https://ollama.ai/install.sh | sh`
- **Permission denied**: Make sure scripts are executable with `chmod +x`
- **Dependencies missing**: Run `pip3 install -r requirements.txt`

### Debug Mode
Launch with debug output:
```bash
python3 -u ai_terminal_gui.py
```

## 🎯 Roadmap

- [ ] Voice input/output support
- [ ] Custom keyboard shortcuts
- [ ] Plugin system for extensions
- [ ] Multi-language support
- [ ] Advanced automation scripting
- [ ] Integration with system notifications

---

**Made with ❤️ for the AI-Native Linux OS project**

*The future of human-computer interaction is conversational!* 

# AI-Native Linux OS: Multi-Agent Terminal

## 🚀 Quick Install (One-Liner)

**To install everything (clone, dependencies, LLM, systemd service) in one go:**

```bash
git clone https://github.com/Orcadebug/Linux.git && \
cd Linux/ai-native-linux-os && \
chmod +x scripts/install-ai-terminal.sh && \
./scripts/install-ai-terminal.sh && \
curl -fsSL https://ollama.com/install.sh | sh && \
ollama pull phi3:mini && \
sudo ./scripts/start-ai-orchestrator.sh install-service && \
sudo systemctl start ai-orchestrator
```

---

## 🛠️ Full Manual Install Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Orcadebug/Linux.git
   cd Linux/ai-native-linux-os
   ```

2. **Install System Dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip git build-essential
   # For GPU/LLM acceleration (optional):
   sudo apt install -y nvidia-driver nvidia-cuda-toolkit
   ```

3. **Run the Install Script**
   ```bash
   chmod +x scripts/install-ai-terminal.sh
   ./scripts/install-ai-terminal.sh
   ```
   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Install Ollama and LLM Models**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull phi3:mini
   ollama pull llama3
   ```

5. **Install as a System Service**
   ```bash
   sudo ./scripts/start-ai-orchestrator.sh install-service
   sudo systemctl start ai-orchestrator
   sudo systemctl enable ai-orchestrator
   ```

6. **Launch the GUI**
   ```bash
   cd src/ai_shell
   python3 ai_terminal_gui.py
   ```

---

## 🧑‍💻 Updating

```bash
cd Linux
git pull
cd ai-native-linux-os
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ai-orchestrator
```

---

## 📝 Notes
- The orchestrator runs as a background service (systemd)
- GUI can be launched from any user session
- All agents are coordinated and hardware-aware
- For advanced usage, see the scripts and config files in the repo 