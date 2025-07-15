#!/usr/bin/env python3
"""
Shell Assistant Agent - Natural language command translation and interactive shell help
"""

import asyncio
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shlex

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

from .base_agent import BaseAgent, AgentMessage, MessageType, AgentState


class CommandSuggestion:
    """Data structure for command suggestions"""
    
    def __init__(self, command: str, description: str, safety_level: str = "safe", examples: List[str] = None):
        self.command = command
        self.description = description
        self.safety_level = safety_level  # safe, caution, dangerous
        self.examples = examples or []
        self.timestamp = datetime.now()


class ShellAssistantAgent(BaseAgent):
    """Agent for natural language shell command translation and assistance"""
    
    def __init__(self, agent_id: str, security_manager, config: Dict):
        super().__init__(agent_id, security_manager, config)
        self.name = "Shell Assistant Agent"
        self.description = "Translates natural language to shell commands with safety checks"
        
        # Shell configuration
        self.shell_config = {
            "max_history": config.get('max_history', 100),
            "safety_check": config.get('safety_check', True),
            "auto_execute": config.get('auto_execute', False),
            "context_aware": config.get('context_aware', True),
            "beginner_mode": config.get('beginner_mode', True),
            "shell_type": config.get('shell_type', 'bash')  # bash, zsh, fish
        }
        
        # Command history and context
        self.command_history = []
        self.conversation_context = []
        self.current_directory = os.getcwd()
        self.environment_state = dict(os.environ)
        
        # Safety and filtering
        self.dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'rm\s+/.*',
            r'dd\s+if=.*of=/dev/',
            r'mkfs\.',
            r'fdisk.*',
            r'format\s+',
            r'del\s+/[sf]',
            r'chmod\s+777\s+/',
            r'chown.*root.*/',
            r'sudo\s+rm\s+-rf\s+/',
            r':\(\)\{.*\|\&\}',  # Fork bomb
            r'wget.*\|\s*sh',
            r'curl.*\|\s*sh',
        ]
        
        # Command templates for AI/ML workflows
        self.ml_templates = self._load_ml_templates()
        
        # Learning mode suggestions
        self.beginner_suggestions = self._load_beginner_suggestions()
        
        self.logger.info("Shell Assistant Agent initialized")
    
    def _load_ml_templates(self) -> Dict:
        """Load AI/ML command templates"""
        return {
            'pytorch_setup': {
                'cuda': """# Setting up PyTorch with CUDA {version}
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu{cuda_version}
python3 -c "import torch; print(f'PyTorch: {{torch.__version__}}'); print(f'CUDA available: {{torch.cuda.is_available()}}')" """,
                'cpu': """# Setting up PyTorch (CPU-only)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python3 -c "import torch; print(f'PyTorch: {{torch.__version__}}')" """
            },
            'tensorflow_setup': {
                'gpu': """# Setting up TensorFlow with GPU support
pip3 install tensorflow[and-cuda]
python3 -c "import tensorflow as tf; print(f'TensorFlow: {{tf.__version__}}'); print(f'GPU: {{len(tf.config.list_physical_devices('GPU'))}} devices')" """,
                'cpu': """# Setting up TensorFlow (CPU-only)
pip3 install tensorflow
python3 -c "import tensorflow as tf; print(f'TensorFlow: {{tf.__version__}}')" """
            },
            'jupyter_setup': """# Install Jupyter Lab with AI/ML extensions
pip3 install jupyterlab ipywidgets
pip3 install jupyterlab-git jupyterlab-lsp
jupyter lab build""",
            'environment_template': """# Create AI/ML environment '{name}'
python3 -m venv {name}
source {name}/bin/activate
pip install --upgrade pip setuptools wheel
echo "Environment '{name}' created! Activate with: source {name}/bin/activate" """,
            'dataset_downloads': {
                'cifar10': """# Download CIFAR-10 dataset
python3 -c "
import torchvision.datasets as datasets
datasets.CIFAR10(root='./data', train=True, download=True)
datasets.CIFAR10(root='./data', train=False, download=True)
print('CIFAR-10 downloaded to ./data/')
" """,
                'mnist': """# Download MNIST dataset
python3 -c "
import torchvision.datasets as datasets
datasets.MNIST(root='./data', train=True, download=True)
datasets.MNIST(root='./data', train=False, download=True)
print('MNIST downloaded to ./data/')
" """
            }
        }
    
    def _load_beginner_suggestions(self) -> Dict:
        """Load beginner-friendly command suggestions"""
        return {
            'navigation': [
                CommandSuggestion("ls -la", "List all files and folders with details", "safe", ["ls", "ls -l", "ls -a"]),
                CommandSuggestion("cd /path/to/directory", "Change to a specific directory", "safe", ["cd ..", "cd ~", "cd /home"]),
                CommandSuggestion("pwd", "Show current directory path", "safe"),
                CommandSuggestion("find . -name 'filename'", "Search for files by name", "safe", ["find . -type f", "find . -name '*.py'"])
            ],
            'file_operations': [
                CommandSuggestion("cp source destination", "Copy files or directories", "safe", ["cp file.txt backup.txt", "cp -r folder/ backup/"]),
                CommandSuggestion("mv old_name new_name", "Move or rename files", "caution", ["mv file.txt newfile.txt"]),
                CommandSuggestion("mkdir directory_name", "Create a new directory", "safe", ["mkdir -p path/to/dir"]),
                CommandSuggestion("touch filename", "Create an empty file", "safe")
            ],
            'system_info': [
                CommandSuggestion("top", "Show running processes", "safe", ["htop", "ps aux"]),
                CommandSuggestion("df -h", "Show disk space usage", "safe"),
                CommandSuggestion("free -h", "Show memory usage", "safe"),
                CommandSuggestion("uname -a", "Show system information", "safe")
            ],
            'ai_ml': [
                CommandSuggestion("python3 -m venv myenv", "Create Python virtual environment", "safe"),
                CommandSuggestion("pip install package_name", "Install Python package", "safe"),
                CommandSuggestion("jupyter lab", "Start Jupyter Lab", "safe"),
                CommandSuggestion("nvidia-smi", "Show GPU status", "safe")
            ]
        }
    
    async def process_message(self, message: AgentMessage) -> Optional[Dict]:
        """Process shell assistance requests"""
        try:
            if message.type == MessageType.TASK:
                return await self._handle_shell_task(message.content)
            elif message.type == MessageType.QUERY:
                return await self._handle_shell_query(message.content)
            else:
                return await super().process_message(message)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def _handle_shell_task(self, content: Dict) -> Dict:
        """Handle shell command requests"""
        task_type = content.get('type', 'translate')
        
        if task_type == 'translate':
            query = content.get('query', '')
            return await self._translate_natural_language(query)
        
        elif task_type == 'execute':
            command = content.get('command', '')
            confirm = content.get('confirm', False)
            return await self._execute_command(command, confirm)
        
        elif task_type == 'explain':
            command = content.get('command', '')
            return await self._explain_command(command)
        
        elif task_type == 'suggest':
            context = content.get('context', '')
            return await self._suggest_commands(context)
        
        elif task_type == 'setup_environment':
            env_type = content.get('env_type', 'python')
            name = content.get('name', 'myenv')
            return await self._setup_environment(env_type, name)
        
        elif task_type == 'tutorial':
            topic = content.get('topic', 'basics')
            return await self._provide_tutorial(topic)
        
        else:
            return {"error": f"Unknown task type: {task_type}", "status": "failed"}
    
    async def _handle_shell_query(self, content: Dict) -> Dict:
        """Handle queries about shell commands and system"""
        query_type = content.get('type', 'help')
        
        if query_type == 'help':
            topic = content.get('topic', 'general')
            return await self._provide_help(topic)
        
        elif query_type == 'history':
            limit = content.get('limit', 20)
            return await self._get_command_history(limit)
        
        elif query_type == 'context':
            return await self._get_current_context()
        
        elif query_type == 'suggestions':
            category = content.get('category', 'all')
            return await self._get_command_suggestions(category)
        
        elif query_type == 'safety_check':
            command = content.get('command', '')
            return await self._check_command_safety(command)
        
        else:
            return {"error": f"Unknown query type: {query_type}", "status": "failed"}
    
    async def _translate_natural_language(self, query: str) -> Dict:
        """Translate natural language to shell commands"""
        try:
            query_lower = query.lower().strip()
            
            # Add to conversation context
            self.conversation_context.append({
                'timestamp': datetime.now(),
                'user_input': query,
                'type': 'request'
            })
            
            # Try rule-based translation first
            command = await self._rule_based_translation(query_lower)
            
            if not command and OLLAMA_AVAILABLE:
                # Fallback to LLM translation
                command = await self._llm_translation(query)
            
            if not command:
                # Fallback to suggestions
                suggestions = await self._get_similar_commands(query_lower)
                return {
                    "status": "no_translation",
                    "query": query,
                    "suggestions": suggestions,
                    "message": "Could not translate to a specific command. Here are some suggestions:"
                }
            
            # Safety check
            safety_result = await self._check_command_safety(command)
            
            # Add to context
            self.conversation_context.append({
                'timestamp': datetime.now(),
                'command': command,
                'safety': safety_result,
                'type': 'response'
            })
            
            return {
                "status": "success",
                "query": query,
                "command": command,
                "explanation": await self._generate_explanation(command),
                "safety": safety_result,
                "examples": await self._get_command_examples(command)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _rule_based_translation(self, query_lower: str) -> Optional[str]:
        """Rule-based natural language to command translation"""
        
        # File and directory operations
        if "list files" in query_lower or "show files" in query_lower:
            if "hidden" in query_lower or "all" in query_lower:
                return "ls -la"
            elif "details" in query_lower or "long" in query_lower:
                return "ls -l"
            else:
                return "ls"
        
        elif "change directory" in query_lower or "go to" in query_lower:
            # Extract directory path
            patterns = [r"to\s+([/\w\-._]+)", r"directory\s+([/\w\-._]+)"]
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    return f"cd {match.group(1)}"
            return "cd"
        
        elif "current directory" in query_lower or "where am i" in query_lower:
            return "pwd"
        
        elif "create directory" in query_lower or "make directory" in query_lower:
            match = re.search(r"(?:directory|folder)\s+([/\w\-._]+)", query_lower)
            if match:
                return f"mkdir -p {match.group(1)}"
            return "mkdir"
        
        elif "copy file" in query_lower or "copy" in query_lower and "to" in query_lower:
            return "cp source destination  # Replace 'source' and 'destination' with actual paths"
        
        elif "move file" in query_lower or "rename" in query_lower:
            return "mv old_name new_name  # Replace with actual filenames"
        
        elif "delete file" in query_lower or "remove file" in query_lower:
            if "recursive" in query_lower or "directory" in query_lower:
                return "rm -r directory_name  # ⚠️  This will delete the directory and all contents"
            return "rm filename  # ⚠️  This will permanently delete the file"
        
        # System information
        elif "disk space" in query_lower or "disk usage" in query_lower:
            return "df -h"
        
        elif "memory usage" in query_lower or "ram usage" in query_lower:
            return "free -h"
        
        elif "running processes" in query_lower or "show processes" in query_lower:
            return "ps aux" if "all" in query_lower else "top"
        
        elif "system info" in query_lower or "system information" in query_lower:
            return "uname -a"
        
        elif "cpu usage" in query_lower or "cpu info" in query_lower:
            return "lscpu"
        
        # Network operations
        elif "network" in query_lower and "status" in query_lower:
            return "ip addr show"
        
        elif "ping" in query_lower:
            match = re.search(r"ping\s+([a-zA-Z0-9.-]+)", query_lower)
            if match:
                return f"ping {match.group(1)}"
            return "ping google.com"
        
        elif "download" in query_lower and any(word in query_lower for word in ["wget", "curl", "http"]):
            if "wget" in query_lower:
                return "wget URL"
            else:
                return "curl -O URL"
        
        # AI/ML specific commands
        ai_ml_command = await self._translate_ai_ml_commands(query_lower)
        if ai_ml_command:
            return ai_ml_command
        
        # Package management
        elif "install package" in query_lower or "install" in query_lower:
            if "python" in query_lower or "pip" in query_lower:
                match = re.search(r"(?:install|pip)\s+([a-zA-Z0-9\-_]+)", query_lower)
                if match:
                    return f"pip3 install {match.group(1)}"
                return "pip3 install package_name"
            elif "apt" in query_lower or "ubuntu" in query_lower:
                return "sudo apt update && sudo apt install package_name"
            
        elif "update system" in query_lower:
            return "sudo apt update && sudo apt upgrade"
        
        # Text operations
        elif "search" in query_lower and "file" in query_lower:
            pattern = r"search.*?['\"]([^'\"]+)['\"]"
            match = re.search(pattern, query_lower)
            if match:
                return f"grep -r '{match.group(1)}' ."
            return "grep -r 'search_term' ."
        
        elif "find file" in query_lower:
            pattern = r"find.*?['\"]([^'\"]+)['\"]"
            match = re.search(pattern, query_lower)
            if match:
                return f"find . -name '{match.group(1)}'"
            return "find . -name 'filename'"
        
        # Archive operations
        elif "extract" in query_lower or "unzip" in query_lower:
            if "tar" in query_lower:
                return "tar -xzf archive.tar.gz"
            else:
                return "unzip archive.zip"
        
        elif "compress" in query_lower or "archive" in query_lower:
            if "tar" in query_lower:
                return "tar -czf archive.tar.gz files/"
            else:
                return "zip -r archive.zip files/"
        
        # Permissions
        elif "permission" in query_lower or "chmod" in query_lower:
            if "executable" in query_lower:
                return "chmod +x filename"
            elif "read" in query_lower and "write" in query_lower:
                return "chmod 644 filename"
            return "chmod 755 filename"
        
        # Process management
        elif "kill process" in query_lower:
            if "name" in query_lower:
                return "pkill process_name"
            return "kill PID"
        
        elif "background" in query_lower and "process" in query_lower:
            return "command &"
        
        # Environment variables
        elif "environment variable" in query_lower or "export" in query_lower:
            return "export VARIABLE_NAME=value"
        
        elif "show environment" in query_lower:
            return "env"
        
        return None
    
    async def _translate_ai_ml_commands(self, query_lower: str) -> Optional[str]:
        """Translate AI/ML specific commands"""
        
        # GPU information
        if any(phrase in query_lower for phrase in ["gpu status", "gpu info", "nvidia"]):
            if GPU_AVAILABLE:
                return "nvidia-smi"
            else:
                return "# No GPU detected or nvidia-smi not available\nlspci | grep -i vga"
        
        elif "gpu memory" in query_lower:
            return "nvidia-smi --query-gpu=memory.used,memory.total --format=csv"
        
        elif "monitor gpu" in query_lower:
            return "watch -n 1 nvidia-smi"
        
        # PyTorch setup
        elif "setup pytorch" in query_lower or "install pytorch" in query_lower:
            gpu_info = await self._get_gpu_info()
            cuda_version = await self._get_cuda_version()
            if gpu_info and cuda_version:
                cuda_ver = cuda_version.replace('.', '')
                return self.ml_templates['pytorch_setup']['cuda'].format(
                    version=cuda_version, cuda_version=cuda_ver
                )
            else:
                return self.ml_templates['pytorch_setup']['cpu']
        
        # TensorFlow setup
        elif "setup tensorflow" in query_lower or "install tensorflow" in query_lower:
            gpu_info = await self._get_gpu_info()
            if gpu_info:
                return self.ml_templates['tensorflow_setup']['gpu']
            else:
                return self.ml_templates['tensorflow_setup']['cpu']
        
        # Environment creation
        elif "create environment" in query_lower or "virtual environment" in query_lower:
            match = re.search(r"(?:environment|env)\s+([a-zA-Z0-9_]+)", query_lower)
            env_name = match.group(1) if match else "ai_env"
            return self.ml_templates['environment_template'].format(name=env_name)
        
        # Jupyter
        elif "start jupyter" in query_lower:
            return "jupyter lab --ip=0.0.0.0 --port=8888 --no-browser"
        
        elif "install jupyter" in query_lower:
            return self.ml_templates['jupyter_setup']
        
        # Dataset downloads
        elif "download" in query_lower and "dataset" in query_lower:
            if "cifar" in query_lower:
                return self.ml_templates['dataset_downloads']['cifar10']
            elif "mnist" in query_lower:
                return self.ml_templates['dataset_downloads']['mnist']
        
        # Training commands
        elif "start training" in query_lower:
            gpu_info = await self._get_gpu_info()
            if gpu_info and len(gpu_info) > 1:
                return f"""# Start distributed training on {len(gpu_info)} GPUs
python3 -m torch.distributed.launch --nproc_per_node={len(gpu_info)} train.py"""
            elif gpu_info:
                return "CUDA_VISIBLE_DEVICES=0 python3 train.py"
            else:
                return "python3 train.py  # CPU training"
        
        elif "monitor training" in query_lower:
            return """# Monitor training progress
# Terminal 1 - TensorBoard:
tensorboard --logdir=runs --port=6006
# Terminal 2 - GPU monitoring:
watch -n 1 nvidia-smi"""
        
        return None
    
    async def _llm_translation(self, query: str) -> Optional[str]:
        """Use LLM for command translation"""
        try:
            if not OLLAMA_AVAILABLE:
                return None
            
            system_prompt = f"""You are a helpful shell command assistant. Convert natural language requests into appropriate shell commands.

Current context:
- Directory: {self.current_directory}
- Shell: {self.shell_config['shell_type']}
- OS: Linux

Rules:
1. Return ONLY the command, no explanation
2. Use safe commands when possible
3. Add safety comments for dangerous operations
4. Consider the current directory context
5. Use standard Linux/Unix commands

Recent conversation context:
{self._format_conversation_context()}
"""
            
            response = ollama.chat(
                model=self.config.get('model', 'llama3'),
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"Convert to shell command: {query}"}
                ]
            )
            
            command = response['message']['content'].strip()
            
            # Clean up the response (remove markdown, explanations, etc.)
            command = self._clean_llm_response(command)
            
            return command
            
        except Exception as e:
            self.logger.error(f"LLM translation failed: {e}")
            return None
    
    def _clean_llm_response(self, response: str) -> str:
        """Clean LLM response to extract just the command"""
        # Remove markdown code blocks
        response = re.sub(r'```(?:bash|sh|shell)?\n?', '', response)
        response = re.sub(r'```', '', response)
        
        # Take first line if multiple lines
        lines = response.strip().split('\n')
        command = lines[0].strip()
        
        # Remove common prefixes
        command = re.sub(r'^(?:Command:|Shell:|Run:|Execute:)\s*', '', command, flags=re.IGNORECASE)
        
        return command
    
    async def _check_command_safety(self, command: str) -> Dict:
        """Check if command is safe to execute"""
        safety_result = {
            'level': 'safe',
            'warnings': [],
            'requires_confirmation': False,
            'blocked': False
        }
        
        if not command:
            return safety_result
        
        command_lower = command.lower()
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                safety_result['level'] = 'dangerous'
                safety_result['requires_confirmation'] = True
                safety_result['warnings'].append(f"Potentially dangerous command detected: {pattern}")
        
        # Check for specific dangerous operations
        if any(word in command_lower for word in ['rm', 'delete', 'format', 'fdisk']):
            if '/' in command or '-rf' in command:
                safety_result['level'] = 'dangerous'
                safety_result['requires_confirmation'] = True
                safety_result['warnings'].append("File deletion command - use with extreme caution")
        
        if 'sudo' in command_lower:
            safety_result['level'] = 'caution'
            safety_result['requires_confirmation'] = True
            safety_result['warnings'].append("Command requires root privileges")
        
        if any(word in command_lower for word in ['wget', 'curl']) and '|' in command:
            safety_result['level'] = 'dangerous'
            safety_result['requires_confirmation'] = True
            safety_result['warnings'].append("Downloading and executing scripts can be dangerous")
        
        # Check permissions with security manager
        if not await self.security_manager.check_permission(
            self.agent_id, 'command_execution', {'command': command}
        ):
            safety_result['blocked'] = True
            safety_result['level'] = 'blocked'
            safety_result['warnings'].append("Command blocked by security policy")
        
        return safety_result
    
    async def _execute_command(self, command: str, confirm: bool = False) -> Dict:
        """Execute shell command with safety checks"""
        try:
            # Safety check
            safety = await self._check_command_safety(command)
            
            if safety['blocked']:
                return {
                    "status": "blocked",
                    "command": command,
                    "error": "Command blocked by security policy",
                    "safety": safety
                }
            
            if safety['requires_confirmation'] and not confirm:
                return {
                    "status": "requires_confirmation",
                    "command": command,
                    "safety": safety,
                    "message": "This command requires explicit confirmation due to safety concerns"
                }
            
            # Execute command
            start_time = time.time()
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.current_directory
            )
            
            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time
            
            # Store in history
            self.command_history.append({
                'timestamp': datetime.now(),
                'command': command,
                'exit_code': process.returncode,
                'execution_time': execution_time,
                'success': process.returncode == 0
            })
            
            # Limit history size
            if len(self.command_history) > self.shell_config['max_history']:
                self.command_history = self.command_history[-self.shell_config['max_history']:]
            
            return {
                "status": "completed",
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "execution_time": execution_time,
                "safety": safety
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "command": command,
                "error": str(e)
            }
    
    async def _explain_command(self, command: str) -> Dict:
        """Explain what a command does"""
        try:
            explanation = await self._generate_explanation(command)
            examples = await self._get_command_examples(command)
            safety = await self._check_command_safety(command)
            
            return {
                "status": "success",
                "command": command,
                "explanation": explanation,
                "examples": examples,
                "safety": safety,
                "breakdown": await self._break_down_command(command)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _generate_explanation(self, command: str) -> str:
        """Generate explanation for a command"""
        
        # Rule-based explanations for common commands
        explanations = {
            'ls': "Lists files and directories in the current location",
            'ls -l': "Lists files with detailed information (permissions, size, date)",
            'ls -la': "Lists all files including hidden ones with detailed information",
            'pwd': "Shows the current directory path",
            'cd': "Changes the current directory",
            'mkdir': "Creates a new directory",
            'rm': "Removes/deletes files or directories",
            'cp': "Copies files or directories",
            'mv': "Moves or renames files or directories",
            'chmod': "Changes file permissions",
            'chown': "Changes file ownership",
            'df -h': "Shows disk space usage in human-readable format",
            'free -h': "Shows memory usage in human-readable format",
            'top': "Shows running processes and system resource usage",
            'ps aux': "Shows all running processes",
            'grep': "Searches for text patterns in files",
            'find': "Searches for files and directories",
            'wget': "Downloads files from the internet",
            'curl': "Transfers data to/from servers",
            'tar': "Archives and compresses files",
            'zip': "Creates compressed archives",
            'unzip': "Extracts compressed archives",
            'ssh': "Connects to remote systems securely",
            'scp': "Copies files securely between systems",
            'sudo': "Executes commands with administrator privileges",
            'pip3 install': "Installs Python packages",
            'python3': "Runs Python scripts or starts Python interpreter",
            'nvidia-smi': "Shows GPU status and usage information"
        }
        
        # Check for exact matches first
        for cmd, explanation in explanations.items():
            if command.startswith(cmd):
                return explanation
        
        # Generate explanation based on command structure
        if command.startswith('cd '):
            path = command[3:].strip()
            return f"Changes directory to '{path}'"
        
        elif command.startswith('mkdir '):
            dir_name = command[6:].strip()
            return f"Creates a new directory named '{dir_name}'"
        
        elif command.startswith('rm '):
            return "Removes (deletes) the specified files or directories"
        
        elif command.startswith('chmod '):
            return "Changes file permissions for the specified files"
        
        # Fallback explanation
        return f"Executes the command: {command}"
    
    async def _break_down_command(self, command: str) -> Dict:
        """Break down command into components"""
        try:
            parts = shlex.split(command)
            if not parts:
                return {"components": []}
            
            breakdown = {
                "command": parts[0],
                "arguments": parts[1:] if len(parts) > 1 else [],
                "flags": [],
                "parameters": []
            }
            
            for arg in parts[1:]:
                if arg.startswith('-'):
                    breakdown["flags"].append(arg)
                else:
                    breakdown["parameters"].append(arg)
            
            return breakdown
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_command_examples(self, command: str) -> List[str]:
        """Get usage examples for a command"""
        base_cmd = command.split()[0] if command else ""
        
        examples_db = {
            'ls': ['ls', 'ls -l', 'ls -la', 'ls *.txt'],
            'cd': ['cd /home/user', 'cd ..', 'cd ~', 'cd /'],
            'mkdir': ['mkdir newdir', 'mkdir -p path/to/dir'],
            'rm': ['rm file.txt', 'rm -r directory/', 'rm *.tmp'],
            'cp': ['cp file1.txt file2.txt', 'cp -r dir1/ dir2/'],
            'mv': ['mv oldname newname', 'mv file.txt /path/to/destination/'],
            'find': ['find . -name "*.py"', 'find /home -type f -size +100M'],
            'grep': ['grep "pattern" file.txt', 'grep -r "text" .'],
            'chmod': ['chmod 755 script.sh', 'chmod u+x file'],
            'tar': ['tar -czf archive.tar.gz files/', 'tar -xzf archive.tar.gz'],
            'pip3': ['pip3 install numpy', 'pip3 list', 'pip3 uninstall package']
        }
        
        return examples_db.get(base_cmd, [])
    
    async def _get_gpu_info(self) -> List[Dict]:
        """Get GPU information"""
        try:
            if not GPU_AVAILABLE:
                return []
            
            gpus = GPUtil.getGPUs()
            return [{
                'id': gpu.id,
                'name': gpu.name,
                'memory_total': gpu.memoryTotal,
                'memory_used': gpu.memoryUsed,
                'load': gpu.load,
                'temperature': gpu.temperature
            } for gpu in gpus]
        except:
            return []
    
    async def _get_cuda_version(self) -> Optional[str]:
        """Get CUDA version"""
        try:
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version_match = re.search(r'release (\d+\.\d+)', result.stdout)
                if version_match:
                    return version_match.group(1)
        except:
            pass
        return None
    
    def _format_conversation_context(self) -> str:
        """Format recent conversation context"""
        if not self.conversation_context:
            return "No recent context"
        
        context_lines = []
        for item in self.conversation_context[-5:]:  # Last 5 interactions
            if item['type'] == 'request':
                context_lines.append(f"User: {item['user_input']}")
            elif item['type'] == 'response':
                context_lines.append(f"Command: {item['command']}")
        
        return '\n'.join(context_lines)
    
    async def _get_similar_commands(self, query: str) -> List[Dict]:
        """Get similar commands based on query"""
        # Simple keyword matching for suggestions
        suggestions = []
        
        if "file" in query:
            suggestions.extend(self.beginner_suggestions['file_operations'])
        if "directory" in query or "folder" in query:
            suggestions.extend(self.beginner_suggestions['navigation'])
        if "system" in query or "info" in query:
            suggestions.extend(self.beginner_suggestions['system_info'])
        if "gpu" in query or "ai" in query or "ml" in query:
            suggestions.extend(self.beginner_suggestions['ai_ml'])
        
        # Convert to dict format
        return [
            {
                "command": s.command,
                "description": s.description,
                "safety": s.safety_level,
                "examples": s.examples
            }
            for s in suggestions[:5]  # Limit to 5 suggestions
        ]
    
    async def get_status(self) -> Dict:
        """Get agent status"""
        status = await super().get_status()
        status.update({
            'commands_in_history': len(self.command_history),
            'current_directory': self.current_directory,
            'shell_type': self.shell_config['shell_type'],
            'safety_enabled': self.shell_config['safety_check'],
            'ollama_available': OLLAMA_AVAILABLE,
            'gpu_available': GPU_AVAILABLE
        })
        return status
    
    async def cleanup(self):
        """Cleanup agent resources"""
        # Save command history if needed
        # Could implement persistent history storage here
        await super().cleanup() 