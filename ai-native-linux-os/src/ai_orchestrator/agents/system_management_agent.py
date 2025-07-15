#!/usr/bin/env python3
"""
System Management Agent - Handles installations, updates, and system tweaks
Uses tiny LLM for efficient, domain-specific processing
"""

import asyncio
import subprocess
import logging
import os
import json
from typing import Dict, List, Optional, Any
import psutil
import platform
import time

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent

class SystemManagementAgent(BaseAgent):
    """
    Specialized agent for system management tasks
    - Software installation and removal
    - System updates and upgrades
    - Service management
    - System configuration
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "SystemManagement"
        self.tiny_model = "phi3:mini"  # Tiny LLM for this domain
        self.capabilities = [
            "install_software",
            "remove_software", 
            "update_system",
            "manage_services",
            "system_info",
            "configure_system"
        ]
        self.package_managers = self._detect_package_managers()
        
    def _detect_package_managers(self) -> List[str]:
        """Detect available package managers"""
        managers = []
        commands = {
            'apt': 'apt-get --version',
            'yum': 'yum --version',
            'dnf': 'dnf --version',
            'pacman': 'pacman --version',
            'snap': 'snap --version',
            'flatpak': 'flatpak --version'
        }
        
        for manager, check_cmd in commands.items():
            try:
                subprocess.run(check_cmd.split(), capture_output=True, check=True)
                managers.append(manager)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
                
        return managers
    
    async def handle(self, query: str) -> str:
        """Handle system management queries with tiny LLM"""
        try:
            # Use tiny LLM for domain-specific classification
            if OLLAMA_AVAILABLE:
                classification_prompt = f"""
                Classify this system management query into one category:
                - install: Install software/packages
                - remove: Remove/uninstall software
                - update: Update system or packages
                - service: Manage system services
                - info: Get system information
                - config: Configure system settings
                
                Query: {query}
                
                Respond with just the category name.
                """
                
                try:
                    response = ollama.generate(model=self.tiny_model, prompt=classification_prompt)
                    category = response['response'].strip().lower()
                except Exception as e:
                    logging.warning(f"LLM classification failed: {e}")
                    category = self._fallback_classify(query)
            else:
                category = self._fallback_classify(query)
            
            # Route to appropriate handler
            if category == 'install':
                return await self._handle_install(query)
            elif category == 'remove':
                return await self._handle_remove(query)
            elif category == 'update':
                return await self._handle_update(query)
            elif category == 'service':
                return await self._handle_service(query)
            elif category == 'info':
                return await self._handle_info(query)
            elif category == 'config':
                return await self._handle_config(query)
            else:
                return await self._handle_general(query)
                
        except Exception as e:
            logging.error(f"SystemManagementAgent error: {e}")
            return f"Error processing system management request: {str(e)}"
    
    def _fallback_classify(self, query: str) -> str:
        """Fallback classification without LLM"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['install', 'add', 'setup', 'get']):
            return 'install'
        elif any(word in query_lower for word in ['remove', 'uninstall', 'delete']):
            return 'remove'
        elif any(word in query_lower for word in ['update', 'upgrade', 'patch']):
            return 'update'
        elif any(word in query_lower for word in ['service', 'daemon', 'start', 'stop', 'restart']):
            return 'service'
        elif any(word in query_lower for word in ['info', 'status', 'system', 'hardware']):
            return 'info'
        elif any(word in query_lower for word in ['config', 'configure', 'settings']):
            return 'config'
        else:
            return 'general'
    
    async def _handle_install(self, query: str) -> str:
        """Handle software installation"""
        try:
            # Extract package name using LLM or patterns
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the software/package name from this installation request:
                "{query}"
                
                Respond with just the package name, nothing else.
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                package = response['response'].strip()
            else:
                # Simple pattern matching fallback
                words = query.lower().split()
                package = None
                for i, word in enumerate(words):
                    if word in ['install', 'add', 'get'] and i + 1 < len(words):
                        package = words[i + 1]
                        break
                if not package:
                    return "Please specify which software to install."
            
            # Install using available package manager
            if 'apt' in self.package_managers:
                cmd = f"sudo apt update && sudo apt install -y {package}"
            elif 'yum' in self.package_managers:
                cmd = f"sudo yum install -y {package}"
            elif 'dnf' in self.package_managers:
                cmd = f"sudo dnf install -y {package}"
            elif 'pacman' in self.package_managers:
                cmd = f"sudo pacman -S --noconfirm {package}"
            else:
                return "No supported package manager found."
            
            # Execute installation
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"✅ Successfully installed {package}"
            else:
                return f"❌ Failed to install {package}: {result.stderr}"
                
        except Exception as e:
            return f"Error during installation: {str(e)}"
    
    async def _handle_remove(self, query: str) -> str:
        """Handle software removal"""
        try:
            # Extract package name
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the software/package name from this removal request:
                "{query}"
                
                Respond with just the package name, nothing else.
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                package = response['response'].strip()
            else:
                words = query.lower().split()
                package = None
                for i, word in enumerate(words):
                    if word in ['remove', 'uninstall', 'delete'] and i + 1 < len(words):
                        package = words[i + 1]
                        break
                if not package:
                    return "Please specify which software to remove."
            
            # Remove using available package manager
            if 'apt' in self.package_managers:
                cmd = f"sudo apt remove -y {package}"
            elif 'yum' in self.package_managers:
                cmd = f"sudo yum remove -y {package}"
            elif 'dnf' in self.package_managers:
                cmd = f"sudo dnf remove -y {package}"
            elif 'pacman' in self.package_managers:
                cmd = f"sudo pacman -R --noconfirm {package}"
            else:
                return "No supported package manager found."
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"✅ Successfully removed {package}"
            else:
                return f"❌ Failed to remove {package}: {result.stderr}"
                
        except Exception as e:
            return f"Error during removal: {str(e)}"
    
    async def _handle_update(self, query: str) -> str:
        """Handle system updates"""
        try:
            if 'apt' in self.package_managers:
                cmd = "sudo apt update && sudo apt upgrade -y"
            elif 'yum' in self.package_managers:
                cmd = "sudo yum update -y"
            elif 'dnf' in self.package_managers:
                cmd = "sudo dnf update -y"
            elif 'pacman' in self.package_managers:
                cmd = "sudo pacman -Syu --noconfirm"
            else:
                return "No supported package manager found."
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return "✅ System updated successfully"
            else:
                return f"❌ Update failed: {result.stderr}"
                
        except Exception as e:
            return f"Error during update: {str(e)}"
    
    async def _handle_service(self, query: str) -> str:
        """Handle service management"""
        try:
            # Extract service name and action
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the service name and action from this service request:
                "{query}"
                
                Respond in format: "action:service_name" (e.g., "start:nginx" or "stop:apache2")
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                parts = response['response'].strip().split(':')
                if len(parts) == 2:
                    action, service = parts
                else:
                    return "Please specify the service and action (start/stop/restart/status)."
            else:
                # Simple pattern matching
                words = query.lower().split()
                action = None
                service = None
                
                for word in words:
                    if word in ['start', 'stop', 'restart', 'status', 'enable', 'disable']:
                        action = word
                        break
                
                for word in words:
                    if word not in ['start', 'stop', 'restart', 'status', 'enable', 'disable', 'service', 'the']:
                        service = word
                        break
                
                if not action or not service:
                    return "Please specify the service and action."
            
            # Execute service command
            cmd = f"sudo systemctl {action} {service}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"✅ Service {service} {action} completed successfully"
            else:
                return f"❌ Service operation failed: {result.stderr}"
                
        except Exception as e:
            return f"Error managing service: {str(e)}"
    
    async def _handle_info(self, query: str) -> str:
        """Handle system information requests"""
        try:
            info = {
                "System": platform.system(),
                "Release": platform.release(),
                "Version": platform.version(),
                "Machine": platform.machine(),
                "Processor": platform.processor(),
                "CPU Cores": psutil.cpu_count(),
                "CPU Usage": f"{psutil.cpu_percent()}%",
                "Memory Total": f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
                "Memory Used": f"{psutil.virtual_memory().percent}%",
                "Disk Usage": f"{psutil.disk_usage('/').percent}%",
                "Boot Time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time()))
            }
            
            formatted_info = "\n".join([f"{k}: {v}" for k, v in info.items()])
            return f"🖥️ System Information:\n{formatted_info}"
            
        except Exception as e:
            return f"Error getting system info: {str(e)}"
    
    async def _handle_config(self, query: str) -> str:
        """Handle system configuration"""
        return "🔧 System configuration features coming soon. Please specify what you'd like to configure."
    
    async def _handle_general(self, query: str) -> str:
        """Handle general system queries"""
        if OLLAMA_AVAILABLE:
            try:
                general_prompt = f"""
                You are a system administration assistant. Help with this query:
                "{query}"
                
                Provide a helpful response about system management, installation, or configuration.
                """
                response = ollama.generate(model=self.tiny_model, prompt=general_prompt)
                return response['response']
            except Exception as e:
                logging.warning(f"General LLM response failed: {e}")
        
        return "I can help with system management tasks like installing software, updating the system, managing services, and getting system information. What would you like to do?"

# Compatibility alias
Agent = SystemManagementAgent 