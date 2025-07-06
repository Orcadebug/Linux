#!/usr/bin/env python3
"""
AI Shell Assistant - Natural language to shell command translation
"""

import os
import sys
import json
import subprocess
import click
import requests
from pathlib import Path


class AIShellAssistant:
    def __init__(self, config_file=None):
        self.config = self.load_config(config_file)
        self.history_file = Path.home() / ".ai_shell_history"
        self.load_history()
    
    def load_config(self, config_file):
        """Load configuration from file or use defaults"""
        default_config = {
            "llm_provider": "local",
            "max_history": 50,
            "safety_check": True,
            "dangerous_commands": ["rm -rf", "dd if=", "mkfs", "format", "fdisk"]
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def load_history(self):
        """Load command history"""
        self.history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = []
    
    def save_history(self):
        """Save command history"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history[-self.config["max_history"]:], f)
    
    def get_context(self):
        """Get current context for AI assistant"""
        context = {
            "cwd": os.getcwd(),
            "user": os.getenv("USER", "unknown"),
            "shell": os.getenv("SHELL", "/bin/bash"),
            "recent_commands": self.history[-5:] if self.history else []
        }
        
        # Add directory listing
        try:
            context["directory_contents"] = os.listdir(".")
        except:
            context["directory_contents"] = []
        
        return context
    
    def is_dangerous_command(self, command):
        """Check if command is potentially dangerous"""
        if not self.config["safety_check"]:
            return False
        
        for dangerous in self.config["dangerous_commands"]:
            if dangerous in command.lower():
                return True
        return False
    
    def translate_natural_language(self, query):
        """Translate natural language to shell command"""
        context = self.get_context()
        
        # Simple rule-based translation for common commands
        query_lower = query.lower()
        
        if "list files" in query_lower or "show files" in query_lower:
            return "ls -la"
        elif "current directory" in query_lower or "where am i" in query_lower:
            return "pwd"
        elif "disk space" in query_lower or "free space" in query_lower:
            return "df -h"
        elif "memory usage" in query_lower or "ram usage" in query_lower:
            return "free -h"
        elif "running processes" in query_lower or "ps" in query_lower:
            return "ps aux"
        elif "create directory" in query_lower or "make directory" in query_lower:
            # Extract directory name from query
            words = query.split()
            if len(words) > 2:
                dir_name = words[-1]
                return f"mkdir -p {dir_name}"
            return "mkdir -p <directory_name>"
        elif "copy file" in query_lower:
            return "cp <source> <destination>"
        elif "move file" in query_lower or "rename file" in query_lower:
            return "mv <source> <destination>"
        elif "delete file" in query_lower or "remove file" in query_lower:
            return "rm <filename>"
        elif "find file" in query_lower or "search file" in query_lower:
            return "find . -name '<filename>'"
        elif "network" in query_lower and "status" in query_lower:
            return "ip addr show"
        elif "system info" in query_lower or "system information" in query_lower:
            return "uname -a"
        else:
            return f"# Could not translate: {query}\n# Try being more specific or use standard shell commands"
    
    def explain_command(self, command):
        """Provide explanation for a shell command"""
        explanations = {
            "ls": "List directory contents",
            "ls -la": "List all files with detailed information",
            "pwd": "Print current working directory",
            "df -h": "Show disk usage in human-readable format",
            "free -h": "Show memory usage in human-readable format",
            "ps aux": "Show all running processes",
            "mkdir": "Create directory",
            "cp": "Copy files or directories",
            "mv": "Move or rename files",
            "rm": "Remove files or directories",
            "find": "Search for files and directories",
            "ip addr show": "Show network interface information",
            "uname -a": "Show system information"
        }
        
        base_cmd = command.split()[0] if command.split() else command
        return explanations.get(base_cmd, f"Command: {command}")
    
    def execute_command(self, command, confirm=True):
        """Execute a shell command with optional confirmation"""
        if self.is_dangerous_command(command):
            click.echo(f"⚠️  WARNING: This command may be dangerous: {command}")
            if not click.confirm("Are you sure you want to continue?"):
                return False
        
        if confirm:
            click.echo(f"Command: {command}")
            click.echo(f"Explanation: {self.explain_command(command)}")
            if not click.confirm("Execute this command?"):
                return False
        
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.stdout:
                click.echo(result.stdout)
            if result.stderr:
                click.echo(f"Error: {result.stderr}", err=True)
            
            # Add to history
            self.history.append({
                "query": command,
                "command": command,
                "success": result.returncode == 0
            })
            self.save_history()
            
            return result.returncode == 0
        except Exception as e:
            click.echo(f"Error executing command: {e}", err=True)
            return False


@click.command()
@click.argument('query', nargs=-1, required=True)
@click.option('--execute', '-e', is_flag=True, help='Execute the command immediately')
@click.option('--explain', '-x', is_flag=True, help='Only explain, don\'t execute')
@click.option('--config', '-c', help='Configuration file path')
def main(query, execute, explain, config):
    """AI Shell Assistant - Translate natural language to shell commands"""
    assistant = AIShellAssistant(config)
    query_text = ' '.join(query)
    
    command = assistant.translate_natural_language(query_text)
    
    if explain:
        click.echo(f"Command: {command}")
        click.echo(f"Explanation: {assistant.explain_command(command)}")
    elif execute:
        assistant.execute_command(command, confirm=False)
    else:
        click.echo(f"Suggested command: {command}")
        click.echo(f"Explanation: {assistant.explain_command(command)}")
        if click.confirm("Execute this command?"):
            assistant.execute_command(command, confirm=False)


if __name__ == '__main__':
    main()