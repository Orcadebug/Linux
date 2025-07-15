# AI-Native Linux OS MVP

An AI-powered Linux distribution with natural language shell assistance, system event logging, AI-driven monitoring, and self-healing capabilities.

## Features

- **AI Shell Assistant**: Natural language to shell command translation with context awareness
- **Quest Log Framework**: System event and command logging with searchable history
- **AI Kernel Monitor**: Intelligent system monitoring with anomaly detection
- **Self-Healing Service**: Automatic service recovery and restart capabilities

## Project Structure

```
ai-native-linux-os/
├── src/
│   ├── ai_shell/          # AI Shell Assistant
│   ├── quest_log/         # Quest Log daemon and CLI
│   ├── kernel_monitor/    # AI Kernel Monitor
│   └── self_healing/      # Self-Healing Service
├── build/                 # Build scripts and ISO remastering
├── scripts/               # Installation and setup scripts
├── tests/                 # Test suites
└── docs/                  # Documentation
```

## Build Timeline

- **Week 1**: Foundation setup and base OS selection
- **Week 2**: Core feature implementation
- **Week 3**: Integration and polish
- **Week 4**: Testing and validation

## Quick Start

### 🚀 One-Line Install (Recommended)

Install everything in one command (requires `sudo`):

```bash
curl -sSL https://raw.githubusercontent.com/Orcadebug/Linux/main/ai-native-linux-os/install.sh | sudo bash
```

This installs:
- System dependencies and Python environment
- Ollama LLM server and models
- AI components and mixture of agents
- Command-line tools (`ai`, `ai-terminal`, `quest`)
- Background systemd services
- Desktop integration

After installation, try:
```bash
ai "list my files"           # Natural language commands
ai-terminal                  # Launch GUI interface
quest commands --recent      # View command history
```

### Option 1: Visual Interface (Manual Install)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Orcadebug/Linux.git
   cd Linux/ai-native-linux-os
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the web interface:**
   ```bash
   python3 src/web_interface/app.py
   ```

4. **Open your browser and go to:**
   ```
   http://localhost:8080
   ```

5. **Follow the interactive tutorial and start building AI projects!**

### Option 2: Command Line Interface (For Advanced Users)

1. **Run individual components:**
   ```bash
   # AI Shell Assistant
   python3 src/ai_shell/ai_shell.py

   # Quest Log Daemon
   python3 src/quest_log/quest_log_daemon.py

   # Kernel Monitor
   python3 src/kernel_monitor/kernel_monitor.py

   # Self-Healing Service
   python3 src/self_healing/self_healing.py
   ```

2. **Run tests:**
   ```bash
   cd tests
   bash run_tests.sh
   ```

## Target Users

- **Primary**: AI/ML developers seeking streamlined environment setup
- **Secondary**: Non-technical users wanting to learn AI through guided projects
- **Tertiary**: System administrators interested in AI-enhanced monitoring