#!/usr/bin/env python3
"""
Security Manager - Handles permissions, sandboxing, and security checks for AI agents
"""

import logging
import os
import re
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import json
import hashlib


class PermissionLevel(Enum):
    NONE = 0
    READ_ONLY = 1
    LIMITED_WRITE = 2
    FULL_ACCESS = 3
    SYSTEM_ADMIN = 4


class AgentPermissions:
    def __init__(self, agent_name: str, permissions: Dict):
        self.agent_name = agent_name
        self.system_commands = permissions.get("system_commands", False)
        self.file_write = permissions.get("file_write", False)
        self.network_access = permissions.get("network_access", False)
        self.process_control = permissions.get("process_control", False)
        self.allowed_paths = set(permissions.get("allowed_paths", []))
        self.forbidden_paths = set(permissions.get("forbidden_paths", []))
        self.max_file_size = permissions.get("max_file_size", 100 * 1024 * 1024)  # 100MB
        self.max_execution_time = permissions.get("max_execution_time", 300)  # 5 minutes
        self.dangerous_commands = set(permissions.get("dangerous_commands", []))


class SecurityManager:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("SecurityManager")
        
        # Permission matrix for agents
        self.agent_permissions = {
            "system_agent": AgentPermissions("system_agent", {
                "system_commands": False,
                "file_write": False,
                "network_access": False,
                "process_control": True,  # read-only process monitoring
                "allowed_paths": ["/proc", "/sys", "/var/log"],
                "forbidden_paths": ["/etc", "/root", "/boot"],
                "dangerous_commands": ["reboot", "shutdown", "kill -9"]
            }),
            
            "file_management_agent": AgentPermissions("file_management_agent", {
                "system_commands": False,
                "file_write": True,
                "network_access": False,
                "process_control": False,
                "allowed_paths": [str(Path.home()), "/tmp", "/var/tmp"],
                "forbidden_paths": ["/etc", "/root", "/boot", "/usr", "/var/log"],
                "max_file_size": 500 * 1024 * 1024,  # 500MB for file operations
                "dangerous_commands": ["rm -rf /", "chmod 777", "chown root"]
            }),
            
            "software_install_agent": AgentPermissions("software_install_agent", {
                "system_commands": True,  # Most privileged agent
                "file_write": True,
                "network_access": True,
                "process_control": True,
                "allowed_paths": ["/", "/usr", "/opt", "/etc"],  # Broad access for installs
                "forbidden_paths": ["/proc", "/sys"],
                "max_execution_time": 1800,  # 30 minutes for complex installs
                "dangerous_commands": ["format", "fdisk", "mkfs"]
            }),
            
            "shell_assistant_agent": AgentPermissions("shell_assistant_agent", {
                "system_commands": True,  # With approval
                "file_write": True,
                "network_access": False,
                "process_control": False,
                "allowed_paths": [str(Path.home()), "/tmp"],
                "forbidden_paths": ["/etc", "/root", "/boot"],
                "dangerous_commands": ["rm -rf", "dd if=", "mkfs", "format"]
            }),
            
            "activity_tracker_agent": AgentPermissions("activity_tracker_agent", {
                "system_commands": False,
                "file_write": True,  # Only for logs
                "network_access": False,
                "process_control": False,
                "allowed_paths": [str(Path.home() / ".ai_logs"), "/tmp"],
                "forbidden_paths": ["/", "/etc", "/root", "/usr"],
                "max_file_size": 50 * 1024 * 1024,  # 50MB for logs
                "dangerous_commands": []
            })
        }
        
        # Global dangerous commands (always require confirmation)
        self.global_dangerous_commands = {
            "rm -rf /", "rm -rf /*", ":(){ :|:& };:", "dd if=/dev/zero",
            "mkfs", "format", "fdisk", "parted", "gparted",
            "chmod -R 777 /", "chown -R root /", "find / -delete",
            "kill -9 -1", "killall -9", "reboot", "shutdown -h now",
            "passwd root", "userdel", "groupdel", "crontab -r",
            "history -c", "unset HISTFILE", "export HISTSIZE=0"
        }
        
        # Audit log
        self.audit_log_path = Path.home() / ".ai_security_audit.log"
        self.setup_audit_logging()
        
        # User confirmation tracking
        self.pending_confirmations = {}
        
    def setup_audit_logging(self):
        """Setup security audit logging"""
        self.audit_logger = logging.getLogger("SecurityAudit")
        handler = logging.FileHandler(self.audit_log_path)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)
    
    def can_execute_task(self, task) -> bool:
        """Check if task can be executed based on security policies"""
        agent_name = task.agent_type
        command = task.command
        
        # Get agent permissions
        permissions = self.agent_permissions.get(agent_name)
        if not permissions:
            self.audit_logger.warning(f"Unknown agent {agent_name} attempted task execution")
            return False
        
        # Check for dangerous commands
        if self.is_dangerous_command(command, permissions):
            self.audit_logger.warning(f"Dangerous command blocked for {agent_name}: {command}")
            if self.config.get("require_confirmation", True):
                return self.request_user_confirmation(task)
            return False
        
        # Check system command permissions
        if self.requires_system_commands(command) and not permissions.system_commands:
            self.audit_logger.warning(f"System command denied for {agent_name}: {command}")
            return False
        
        # Check file write permissions
        if self.requires_file_write(command) and not permissions.file_write:
            self.audit_logger.warning(f"File write denied for {agent_name}: {command}")
            return False
        
        # Check network access
        if self.requires_network_access(command) and not permissions.network_access:
            self.audit_logger.warning(f"Network access denied for {agent_name}: {command}")
            return False
        
        # Check path restrictions
        if not self.check_path_permissions(command, permissions):
            self.audit_logger.warning(f"Path access denied for {agent_name}: {command}")
            return False
        
        # Log successful authorization
        self.audit_logger.info(f"Task authorized for {agent_name}: {command[:100]}")
        return True
    
    def is_dangerous_command(self, command: str, permissions: AgentPermissions) -> bool:
        """Check if command is dangerous"""
        command_lower = command.lower().strip()
        
        # Check global dangerous commands
        for dangerous in self.global_dangerous_commands:
            if dangerous in command_lower:
                return True
        
        # Check agent-specific dangerous commands
        for dangerous in permissions.dangerous_commands:
            if dangerous.lower() in command_lower:
                return True
        
        # Pattern-based checks
        dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'dd\s+if=.*of=/dev/',
            r'chmod\s+-R\s+777\s+/',
            r'find\s+/.*-delete',
            r'kill\s+-9\s+-1',
            r'>\s*/dev/sd[a-z]',
            r'mkfs\.',
            r'fdisk\s+/dev/'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                return True
        
        return False
    
    def requires_system_commands(self, command: str) -> bool:
        """Check if command requires system-level access"""
        system_commands = {
            'sudo', 'su', 'systemctl', 'service', 'mount', 'umount',
            'iptables', 'ufw', 'crontab', 'passwd', 'useradd', 'userdel',
            'groupadd', 'groupdel', 'chown', 'chmod', 'apt', 'yum', 'dnf',
            'pacman', 'zypper', 'snap', 'flatpak', 'docker', 'podman'
        }
        
        words = command.split()
        if words:
            first_word = words[0].lower()
            return first_word in system_commands
        
        return False
    
    def requires_file_write(self, command: str) -> bool:
        """Check if command requires file write access"""
        write_commands = {
            'cp', 'mv', 'mkdir', 'rmdir', 'rm', 'touch', 'echo', 'cat',
            'tee', 'dd', 'tar', 'unzip', 'gunzip', 'gzip', 'wget', 'curl'
        }
        
        # Check for output redirection
        if '>' in command or '>>' in command:
            return True
        
        words = command.split()
        if words:
            first_word = words[0].lower()
            return first_word in write_commands
        
        return False
    
    def requires_network_access(self, command: str) -> bool:
        """Check if command requires network access"""
        network_commands = {
            'wget', 'curl', 'ssh', 'scp', 'rsync', 'ftp', 'sftp',
            'ping', 'telnet', 'nc', 'netcat', 'nmap', 'dig', 'nslookup'
        }
        
        words = command.split()
        if words:
            first_word = words[0].lower()
            return first_word in network_commands
        
        return False
    
    def check_path_permissions(self, command: str, permissions: AgentPermissions) -> bool:
        """Check if command accesses allowed paths"""
        # Extract paths from command
        paths = self.extract_paths_from_command(command)
        
        for path in paths:
            path_obj = Path(path).resolve()
            
            # Check forbidden paths
            for forbidden in permissions.forbidden_paths:
                forbidden_path = Path(forbidden).resolve()
                try:
                    path_obj.relative_to(forbidden_path)
                    return False  # Path is under forbidden directory
                except ValueError:
                    continue
            
            # Check allowed paths (if specified)
            if permissions.allowed_paths:
                allowed = False
                for allowed_path in permissions.allowed_paths:
                    allowed_path_obj = Path(allowed_path).resolve()
                    try:
                        path_obj.relative_to(allowed_path_obj)
                        allowed = True
                        break
                    except ValueError:
                        continue
                
                if not allowed:
                    return False
        
        return True
    
    def extract_paths_from_command(self, command: str) -> List[str]:
        """Extract file paths from command"""
        paths = []
        
        # Simple path extraction (can be improved)
        words = command.split()
        for word in words:
            # Skip flags and options
            if word.startswith('-'):
                continue
            
            # Check if it looks like a path
            if '/' in word or word.startswith('~') or word.startswith('.'):
                paths.append(word)
        
        return paths
    
    def request_user_confirmation(self, task) -> bool:
        """Request user confirmation for dangerous operations"""
        confirmation_id = hashlib.md5(
            f"{task.task_id}{task.command}".encode()
        ).hexdigest()[:8]
        
        self.pending_confirmations[confirmation_id] = {
            'task': task,
            'timestamp': time.time(),
            'confirmed': False
        }
        
        # In a real implementation, this would trigger a GUI dialog
        # For now, we'll just log and return False (denied)
        self.logger.warning(
            f"User confirmation required for dangerous command: {task.command}"
        )
        self.logger.warning(f"Confirmation ID: {confirmation_id}")
        
        return False  # Default to deny for safety
    
    def confirm_dangerous_operation(self, confirmation_id: str, confirmed: bool) -> bool:
        """Confirm or deny a dangerous operation"""
        if confirmation_id not in self.pending_confirmations:
            return False
        
        confirmation = self.pending_confirmations[confirmation_id]
        
        # Check if confirmation hasn't expired (5 minutes)
        if time.time() - confirmation['timestamp'] > 300:
            del self.pending_confirmations[confirmation_id]
            return False
        
        confirmation['confirmed'] = confirmed
        
        if confirmed:
            self.audit_logger.info(
                f"Dangerous operation confirmed: {confirmation['task'].command}"
            )
        else:
            self.audit_logger.info(
                f"Dangerous operation denied: {confirmation['task'].command}"
            )
        
        return True
    
    def sandbox_command(self, command: str, agent_name: str) -> str:
        """Sandbox a command for safe execution"""
        permissions = self.agent_permissions.get(agent_name)
        if not permissions:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        sandboxed_command = command
        
        # Add timeout to prevent long-running processes
        timeout = permissions.max_execution_time
        sandboxed_command = f"timeout {timeout} {sandboxed_command}"
        
        # For file operations, restrict to allowed paths
        if permissions.file_write and permissions.allowed_paths:
            # This is a simplified approach - in production, you'd use
            # more sophisticated sandboxing like chroot, containers, etc.
            pass
        
        return sandboxed_command
    
    def log_agent_activity(self, agent_name: str, action: str, details: Dict = None):
        """Log agent activity for security auditing"""
        log_entry = {
            'timestamp': time.time(),
            'agent': agent_name,
            'action': action,
            'details': details or {}
        }
        
        self.audit_logger.info(json.dumps(log_entry))
    
    def get_security_summary(self) -> Dict:
        """Get security status summary"""
        return {
            'total_agents': len(self.agent_permissions),
            'pending_confirmations': len(self.pending_confirmations),
            'audit_log_size': self.audit_log_path.stat().st_size if self.audit_log_path.exists() else 0,
            'dangerous_commands_blocked': self._count_blocked_commands(),
            'agent_permissions': {
                name: {
                    'system_commands': perms.system_commands,
                    'file_write': perms.file_write,
                    'network_access': perms.network_access,
                    'process_control': perms.process_control
                }
                for name, perms in self.agent_permissions.items()
            }
        }
    
    def _count_blocked_commands(self) -> int:
        """Count blocked commands from audit log"""
        if not self.audit_log_path.exists():
            return 0
        
        count = 0
        try:
            with open(self.audit_log_path, 'r') as f:
                for line in f:
                    if 'blocked' in line.lower() or 'denied' in line.lower():
                        count += 1
        except Exception:
            pass
        
        return count
    
    def emergency_lockdown(self):
        """Emergency lockdown - disable all agent permissions"""
        self.logger.critical("EMERGENCY LOCKDOWN ACTIVATED")
        
        # Save original permissions
        self._original_permissions = self.agent_permissions.copy()
        
        # Disable all permissions
        for agent_name in self.agent_permissions:
            self.agent_permissions[agent_name] = AgentPermissions(agent_name, {
                "system_commands": False,
                "file_write": False,
                "network_access": False,
                "process_control": False,
                "allowed_paths": [],
                "forbidden_paths": ["/"],
                "dangerous_commands": ["*"]  # Block everything
            })
        
        self.audit_logger.critical("Emergency lockdown activated - all permissions revoked")
    
    def restore_from_lockdown(self):
        """Restore permissions after emergency lockdown"""
        if hasattr(self, '_original_permissions'):
            self.agent_permissions = self._original_permissions
            delattr(self, '_original_permissions')
            self.logger.info("Permissions restored from emergency lockdown")
            self.audit_logger.info("Emergency lockdown lifted - permissions restored")
        else:
            self.logger.warning("No original permissions found to restore")


# Testing interface
if __name__ == "__main__":
    # Test security manager
    config = {
        "require_confirmation": True,
        "dangerous_commands": ["rm -rf", "dd if="]
    }
    
    security_manager = SecurityManager(config)
    
    # Test cases
    test_cases = [
        ("system_agent", "ps aux"),
        ("system_agent", "rm -rf /"),
        ("file_management_agent", "mkdir ~/test"),
        ("file_management_agent", "rm -rf /etc"),
        ("software_install_agent", "apt install python3"),
        ("shell_assistant_agent", "ls -la"),
        ("activity_tracker_agent", "echo 'log entry' >> ~/.ai_logs/activity.log")
    ]
    
    print("Security Manager Test Results:")
    print("=" * 50)
    
    for agent, command in test_cases:
        # Create mock task
        class MockTask:
            def __init__(self, agent_type, command):
                self.agent_type = agent_type
                self.command = command
                self.task_id = "test"
        
        task = MockTask(agent, command)
        allowed = security_manager.can_execute_task(task)
        
        print(f"Agent: {agent}")
        print(f"Command: {command}")
        print(f"Allowed: {'✅' if allowed else '❌'}")
        print("-" * 30)
    
    print("\nSecurity Summary:")
    summary = security_manager.get_security_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")