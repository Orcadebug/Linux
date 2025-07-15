#!/usr/bin/env python3
"""
Software Install Agent - Enhanced with async processing and efficiency improvements
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import shutil
import logging

from .base_agent import BaseAgent


class PackageManager:
    """Package manager detection and abstraction"""
    
    MANAGERS = {
        'apt': {
            'install': 'apt install -y',
            'remove': 'apt remove -y',
            'update': 'apt update',
            'upgrade': 'apt upgrade -y',
            'search': 'apt search',
            'list': 'apt list --installed',
            'check': 'dpkg -s'
        },
        'yum': {
            'install': 'yum install -y',
            'remove': 'yum remove -y',
            'update': 'yum update',
            'upgrade': 'yum upgrade -y',
            'search': 'yum search',
            'list': 'yum list installed',
            'check': 'rpm -q'
        },
        'dnf': {
            'install': 'dnf install -y',
            'remove': 'dnf remove -y',
            'update': 'dnf update',
            'upgrade': 'dnf upgrade -y',
            'search': 'dnf search',
            'list': 'dnf list installed',
            'check': 'rpm -q'
        },
        'pacman': {
            'install': 'pacman -S --noconfirm',
            'remove': 'pacman -R --noconfirm',
            'update': 'pacman -Sy',
            'upgrade': 'pacman -Syu --noconfirm',
            'search': 'pacman -Ss',
            'list': 'pacman -Q',
            'check': 'pacman -Q'
        }
    }
    
    @classmethod
    def detect_package_manager(cls) -> Dict[str, bool]:
        """Detect available package managers"""
        available = {}
        
        for manager in cls.MANAGERS.keys():
            available[manager] = shutil.which(manager) is not None
        
        return available
    
    @classmethod
    def get_primary_manager(cls) -> Tuple[str, Dict]:
        """Get the primary package manager for the system"""
        available = cls.detect_package_manager()
        
        # Priority order
        priority = ['apt', 'dnf', 'yum', 'pacman']
        
        for manager in priority:
            if available.get(manager, False):
                return manager, cls.MANAGERS[manager]
        
        return 'apt', cls.MANAGERS['apt']  # Default fallback


class SoftwareInstallAgent(BaseAgent):
    """Enhanced agent for handling software installations and updates"""
    
    def __init__(self, hardware_info: Dict, security_manager, logger):
        super().__init__("software_install_agent", hardware_info, security_manager, logger)
        self.name = "Software Installation Agent"
        self.description = "Handles software installations, updates, and dependency resolution with async processing"
        
        # Configuration
        self.config = {
            "auto_update_before_install": True,
            "create_restore_point": True,
            "max_install_time": 1800,  # 30 minutes
            "retry_failed_installs": 3,
            "check_dependencies": True,
            "safe_mode": True,
            "dry_run": False
        }
        
        # Installation tracking
        self.active_installations = {}
        self.installation_history = []
        self.rollback_points = {}
        
        # Package manager detection
        self.package_managers = PackageManager.detect_package_manager()
        self.primary_manager, self.primary_cmd = PackageManager.get_primary_manager()
        
        # Installation templates for common software
        self.install_templates = {
            'docker': {
                'commands': [
                    'curl -fsSL https://get.docker.com -o get-docker.sh',
                    'sudo sh get-docker.sh',
                    'sudo usermod -aG docker $USER'
                ],
                'verify': 'docker --version',
                'post_install': 'sudo systemctl enable docker'
            },
            'nodejs': {
                'commands': [
                    'curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -',
                    'sudo apt-get install -y nodejs'
                ],
                'verify': 'node --version',
                'post_install': 'npm install -g npm@latest'
            },
            'python': {
                'commands': [
                    'sudo apt update',
                    'sudo apt install -y python3 python3-pip python3-venv'
                ],
                'verify': 'python3 --version',
                'post_install': 'pip3 install --upgrade pip'
            },
            'java': {
                'commands': [
                    'sudo apt update',
                    'sudo apt install -y default-jdk'
                ],
                'verify': 'java -version',
                'post_install': 'sudo update-alternatives --config java'
            },
            'git': {
                'commands': [
                    'sudo apt update',
                    'sudo apt install -y git'
                ],
                'verify': 'git --version',
                'post_install': 'git config --global init.defaultBranch main'
            }
        }
        
        # Statistics tracking
        self.stats = {
            'packages_installed': 0,
            'packages_updated': 0,
            'packages_removed': 0,
            'failed_installations': 0,
            'total_install_time': 0,
            'rollbacks_performed': 0
        }
        
        self.logger.info(f"Enhanced Software Installation Agent initialized with {self.primary_manager}")
    
    def _initialize_rule_patterns(self) -> Dict[str, callable]:
        """Initialize rule-based patterns for software installation"""
        return {
            'install': self._rule_install_software,
            'remove': self._rule_remove_software,
            'update': self._rule_update_software,
            'upgrade': self._rule_upgrade_system,
            'search': self._rule_search_software,
            'list': self._rule_list_installed,
            'verify': self._rule_verify_installation,
            'rollback': self._rule_rollback_installation,
            'docker': self._rule_install_docker,
            'nodejs': self._rule_install_nodejs,
            'python': self._rule_install_python,
            'java': self._rule_install_java,
            'git': self._rule_install_git
        }
    
    async def _process_task_with_llm(self, task) -> Dict:
        """Process software installation task using LLM with safety checks"""
        context = {
            'package_manager': self.primary_manager,
            'available_managers': self.package_managers,
            'install_templates': list(self.install_templates.keys()),
            'safe_mode': self.config['safe_mode']
        }
        
        prompt = f"""
Software installation task: {task.command}

System information:
- Primary package manager: {self.primary_manager}
- Available package managers: {', '.join([k for k, v in self.package_managers.items() if v])}
- Safe mode: {self.config['safe_mode']}

Available installation templates: {', '.join(self.install_templates.keys())}

Provide a specific installation plan with:
1. Package name or software to install
2. Installation method (package manager or custom script)
3. Dependencies to check/install first
4. Verification steps
5. Post-installation configuration
6. Risk assessment (low/medium/high)

Be specific about commands and safety measures. Only suggest safe operations.
"""
        
        response = await self.query_llm(prompt, context)
        
        if response:
            # Parse LLM response and execute safely
            return await self._execute_llm_plan(response, task)
        else:
            # Fallback to rules
            return await self._process_task_with_rules(task)
    
    async def _process_task_with_rules(self, task) -> Dict:
        """Process software installation task using rule-based approach with async processing"""
        try:
            # Yield control for other tasks
            await asyncio.sleep(0)
            
            # Check if package already exists first (efficiency improvement)
            if 'install' in task.command.lower():
                package_name = self._extract_package_name(task.command)
                if package_name and await self._is_package_installed(package_name):
                    return {
                        'success': True,
                        'result': f"{package_name} is already installed",
                        'method': 'rules'
                    }
            
            # Match rule pattern
            handler = self.match_rule_pattern(task.command)
            
            if handler:
                # Execute with safety checks
                if self._requires_confirmation(task.command):
                    confirm = input(f"Confirm software operation: {task.command}? (y/n): ")
                    if confirm.lower() != 'y':
                        return {
                            'success': False,
                            'result': 'Operation cancelled by user',
                            'method': 'rules'
                        }
                
                result = await handler(task.command)
                return {
                    'success': True,
                    'result': result,
                    'method': 'rules'
                }
            else:
                return {
                    'success': False,
                    'error': 'No matching rule pattern found',
                    'method': 'rules'
                }
                
        except Exception as e:
            self.logger.error(f"Rule-based processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'rules'
            }
    
    def _get_agent_description(self) -> str:
        """Get agent-specific description for prompts"""
        return "A software installation agent that handles package management and custom software installations safely"
    
    def _get_supported_operations(self) -> List[str]:
        """Get list of operations this agent supports"""
        return [
            'install', 'remove', 'update', 'upgrade', 'search', 'list', 
            'verify', 'rollback', 'docker', 'nodejs', 'python', 'java', 'git'
        ]
    
    def _requires_confirmation(self, command: str) -> bool:
        """Check if command requires user confirmation"""
        dangerous_keywords = ['remove', 'uninstall', 'purge', 'upgrade', 'dist-upgrade']
        return any(keyword in command.lower() for keyword in dangerous_keywords)
    
    def _extract_package_name(self, command: str) -> Optional[str]:
        """Extract package name from command"""
        # Simple pattern matching - would need more sophisticated parsing
        import re
        
        patterns = [
            r'install\s+([^\s]+)',
            r'remove\s+([^\s]+)',
            r'search\s+([^\s]+)',
            r'verify\s+([^\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    async def _is_package_installed(self, package_name: str) -> bool:
        """Check if package is already installed"""
        try:
            check_cmd = self.primary_cmd['check']
            result = await self._run_command(f"{check_cmd} {package_name}")
            return result['returncode'] == 0
        except Exception:
            return False
    
    async def _run_command(self, command: str, timeout: int = 30) -> Dict:
        """Run command asynchronously with timeout"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return {
                'returncode': process.returncode,
                'stdout': stdout.decode(),
                'stderr': stderr.decode()
            }
            
        except asyncio.TimeoutError:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out'
            }
        except Exception as e:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    async def _execute_llm_plan(self, llm_response: str, task) -> Dict:
        """Execute LLM-generated installation plan with safety checks"""
        try:
            # Parse LLM response (simplified - would need more sophisticated parsing)
            if 'docker' in llm_response.lower():
                return await self._rule_install_docker(task.command)
            elif 'nodejs' in llm_response.lower() or 'node' in llm_response.lower():
                return await self._rule_install_nodejs(task.command)
            elif 'python' in llm_response.lower():
                return await self._rule_install_python(task.command)
            elif 'java' in llm_response.lower():
                return await self._rule_install_java(task.command)
            elif 'install' in llm_response.lower():
                return await self._rule_install_software(task.command)
            else:
                return await self._rule_install_software(task.command)  # Default
                
        except Exception as e:
            self.logger.error(f"LLM plan execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'llm'
            }
    
    # Rule-based handlers with async processing
    async def _rule_install_software(self, command: str) -> str:
        """Install software package with async processing"""
        try:
            package_name = self._extract_package_name(command)
            if not package_name:
                return "Could not extract package name from command"
            
            # Check if already installed
            if await self._is_package_installed(package_name):
                return f"{package_name} is already installed"
            
            start_time = time.time()
            
            # Update package lists if configured
            if self.config['auto_update_before_install']:
                update_result = await self._run_command(
                    f"sudo {self.primary_cmd['update']}", 
                    timeout=300
                )
                if update_result['returncode'] != 0:
                    return f"Failed to update package lists: {update_result['stderr']}"
            
            # Install package
            install_cmd = f"sudo {self.primary_cmd['install']} {package_name}"
            
            if not self.config['dry_run']:
                result = await self._run_command(install_cmd, timeout=self.config['max_install_time'])
                
                if result['returncode'] == 0:
                    # Verify installation
                    if await self._is_package_installed(package_name):
                        install_time = time.time() - start_time
                        self.stats['packages_installed'] += 1
                        self.stats['total_install_time'] += install_time
                        
                        return f"Successfully installed {package_name} in {install_time:.1f}s"
                    else:
                        self.stats['failed_installations'] += 1
                        return f"Installation completed but {package_name} verification failed"
                else:
                    self.stats['failed_installations'] += 1
                    return f"Failed to install {package_name}: {result['stderr']}"
            else:
                return f"Dry run: Would install {package_name}"
                
        except Exception as e:
            self.stats['failed_installations'] += 1
            return f"Installation error: {str(e)}"
    
    async def _rule_remove_software(self, command: str) -> str:
        """Remove software package with async processing"""
        try:
            package_name = self._extract_package_name(command)
            if not package_name:
                return "Could not extract package name from command"
            
            # Check if installed
            if not await self._is_package_installed(package_name):
                return f"{package_name} is not installed"
            
            # Remove package
            remove_cmd = f"sudo {self.primary_cmd['remove']} {package_name}"
            
            if not self.config['dry_run']:
                result = await self._run_command(remove_cmd, timeout=300)
                
                if result['returncode'] == 0:
                    self.stats['packages_removed'] += 1
                    return f"Successfully removed {package_name}"
                else:
                    return f"Failed to remove {package_name}: {result['stderr']}"
            else:
                return f"Dry run: Would remove {package_name}"
                
        except Exception as e:
            return f"Removal error: {str(e)}"
    
    async def _rule_update_software(self, command: str) -> str:
        """Update package lists with async processing"""
        try:
            update_cmd = f"sudo {self.primary_cmd['update']}"
            
            if not self.config['dry_run']:
                result = await self._run_command(update_cmd, timeout=300)
                
                if result['returncode'] == 0:
                    return "Successfully updated package lists"
                else:
                    return f"Failed to update package lists: {result['stderr']}"
            else:
                return "Dry run: Would update package lists"
                
        except Exception as e:
            return f"Update error: {str(e)}"
    
    async def _rule_upgrade_system(self, command: str) -> str:
        """Upgrade system packages with async processing"""
        try:
            upgrade_cmd = f"sudo {self.primary_cmd['upgrade']}"
            
            if not self.config['dry_run']:
                result = await self._run_command(upgrade_cmd, timeout=1800)  # 30 minutes
                
                if result['returncode'] == 0:
                    self.stats['packages_updated'] += 1
                    return "Successfully upgraded system packages"
                else:
                    return f"Failed to upgrade system: {result['stderr']}"
            else:
                return "Dry run: Would upgrade system packages"
                
        except Exception as e:
            return f"Upgrade error: {str(e)}"
    
    async def _rule_search_software(self, command: str) -> str:
        """Search for software packages with async processing"""
        try:
            search_term = self._extract_package_name(command)
            if not search_term:
                return "Could not extract search term from command"
            
            search_cmd = f"{self.primary_cmd['search']} {search_term}"
            result = await self._run_command(search_cmd, timeout=60)
            
            if result['returncode'] == 0:
                # Limit output for readability
                lines = result['stdout'].split('\n')[:20]
                return f"Search results for '{search_term}':\n" + '\n'.join(lines)
            else:
                return f"Search failed: {result['stderr']}"
                
        except Exception as e:
            return f"Search error: {str(e)}"
    
    async def _rule_list_installed(self, command: str) -> str:
        """List installed packages with async processing"""
        try:
            list_cmd = self.primary_cmd['list']
            result = await self._run_command(list_cmd, timeout=60)
            
            if result['returncode'] == 0:
                # Count packages and show first 20
                lines = result['stdout'].split('\n')
                package_count = len([line for line in lines if line.strip()])
                
                return f"Found {package_count} installed packages (showing first 20):\n" + '\n'.join(lines[:20])
            else:
                return f"Failed to list packages: {result['stderr']}"
                
        except Exception as e:
            return f"List error: {str(e)}"
    
    async def _rule_verify_installation(self, command: str) -> str:
        """Verify software installation with async processing"""
        try:
            package_name = self._extract_package_name(command)
            if not package_name:
                return "Could not extract package name from command"
            
            if await self._is_package_installed(package_name):
                # Try to get version info
                try:
                    version_result = await self._run_command(f"{package_name} --version", timeout=10)
                    if version_result['returncode'] == 0:
                        return f"{package_name} is installed: {version_result['stdout'].strip()}"
                    else:
                        return f"{package_name} is installed but version check failed"
                except:
                    return f"{package_name} is installed"
            else:
                return f"{package_name} is not installed"
                
        except Exception as e:
            return f"Verification error: {str(e)}"
    
    async def _rule_rollback_installation(self, command: str) -> str:
        """Rollback installation (placeholder for future implementation)"""
        return "Rollback functionality not yet implemented"
    
    async def _rule_install_docker(self, command: str) -> str:
        """Install Docker using template with async processing"""
        try:
            template = self.install_templates['docker']
            
            if await self._is_package_installed('docker'):
                return "Docker is already installed"
            
            results = []
            
            for cmd in template['commands']:
                if not self.config['dry_run']:
                    result = await self._run_command(cmd, timeout=300)
                    
                    if result['returncode'] != 0:
                        return f"Docker installation failed at step: {cmd}\nError: {result['stderr']}"
                    
                    results.append(f"✓ {cmd}")
                else:
                    results.append(f"Dry run: {cmd}")
            
            # Post-installation
            if not self.config['dry_run'] and template.get('post_install'):
                await self._run_command(template['post_install'], timeout=60)
            
            # Verify
            if not self.config['dry_run']:
                verify_result = await self._run_command(template['verify'], timeout=10)
                if verify_result['returncode'] == 0:
                    self.stats['packages_installed'] += 1
                    return f"Docker installed successfully!\n" + '\n'.join(results)
                else:
                    return f"Docker installation completed but verification failed"
            else:
                return f"Dry run: Would install Docker\n" + '\n'.join(results)
                
        except Exception as e:
            self.stats['failed_installations'] += 1
            return f"Docker installation error: {str(e)}"
    
    async def _rule_install_nodejs(self, command: str) -> str:
        """Install Node.js using template with async processing"""
        try:
            template = self.install_templates['nodejs']
            
            # Check if already installed
            check_result = await self._run_command('node --version', timeout=10)
            if check_result['returncode'] == 0:
                return f"Node.js is already installed: {check_result['stdout'].strip()}"
            
            results = []
            
            for cmd in template['commands']:
                if not self.config['dry_run']:
                    result = await self._run_command(cmd, timeout=300)
                    
                    if result['returncode'] != 0:
                        return f"Node.js installation failed at step: {cmd}\nError: {result['stderr']}"
                    
                    results.append(f"✓ {cmd}")
                else:
                    results.append(f"Dry run: {cmd}")
            
            # Post-installation
            if not self.config['dry_run'] and template.get('post_install'):
                await self._run_command(template['post_install'], timeout=60)
            
            # Verify
            if not self.config['dry_run']:
                verify_result = await self._run_command(template['verify'], timeout=10)
                if verify_result['returncode'] == 0:
                    self.stats['packages_installed'] += 1
                    return f"Node.js installed successfully: {verify_result['stdout'].strip()}\n" + '\n'.join(results)
                else:
                    return f"Node.js installation completed but verification failed"
            else:
                return f"Dry run: Would install Node.js\n" + '\n'.join(results)
                
        except Exception as e:
            self.stats['failed_installations'] += 1
            return f"Node.js installation error: {str(e)}"
    
    async def _rule_install_python(self, command: str) -> str:
        """Install Python using template with async processing"""
        try:
            template = self.install_templates['python']
            
            # Check if already installed
            check_result = await self._run_command('python3 --version', timeout=10)
            if check_result['returncode'] == 0:
                return f"Python is already installed: {check_result['stdout'].strip()}"
            
            results = []
            
            for cmd in template['commands']:
                if not self.config['dry_run']:
                    result = await self._run_command(cmd, timeout=300)
                    
                    if result['returncode'] != 0:
                        return f"Python installation failed at step: {cmd}\nError: {result['stderr']}"
                    
                    results.append(f"✓ {cmd}")
                else:
                    results.append(f"Dry run: {cmd}")
            
            # Post-installation
            if not self.config['dry_run'] and template.get('post_install'):
                await self._run_command(template['post_install'], timeout=60)
            
            # Verify
            if not self.config['dry_run']:
                verify_result = await self._run_command(template['verify'], timeout=10)
                if verify_result['returncode'] == 0:
                    self.stats['packages_installed'] += 1
                    return f"Python installed successfully: {verify_result['stdout'].strip()}\n" + '\n'.join(results)
                else:
                    return f"Python installation completed but verification failed"
            else:
                return f"Dry run: Would install Python\n" + '\n'.join(results)
                
        except Exception as e:
            self.stats['failed_installations'] += 1
            return f"Python installation error: {str(e)}"
    
    async def _rule_install_java(self, command: str) -> str:
        """Install Java using template with async processing"""
        try:
            template = self.install_templates['java']
            
            # Check if already installed
            check_result = await self._run_command('java -version', timeout=10)
            if check_result['returncode'] == 0:
                return f"Java is already installed: {check_result['stderr'].strip()}"  # Java outputs version to stderr
            
            results = []
            
            for cmd in template['commands']:
                if not self.config['dry_run']:
                    result = await self._run_command(cmd, timeout=300)
                    
                    if result['returncode'] != 0:
                        return f"Java installation failed at step: {cmd}\nError: {result['stderr']}"
                    
                    results.append(f"✓ {cmd}")
                else:
                    results.append(f"Dry run: {cmd}")
            
            # Verify
            if not self.config['dry_run']:
                verify_result = await self._run_command(template['verify'], timeout=10)
                if verify_result['returncode'] == 0:
                    self.stats['packages_installed'] += 1
                    return f"Java installed successfully!\n" + '\n'.join(results)
                else:
                    return f"Java installation completed but verification failed"
            else:
                return f"Dry run: Would install Java\n" + '\n'.join(results)
                
        except Exception as e:
            self.stats['failed_installations'] += 1
            return f"Java installation error: {str(e)}"
    
    async def _rule_install_git(self, command: str) -> str:
        """Install Git using template with async processing"""
        try:
            template = self.install_templates['git']
            
            # Check if already installed
            check_result = await self._run_command('git --version', timeout=10)
            if check_result['returncode'] == 0:
                return f"Git is already installed: {check_result['stdout'].strip()}"
            
            results = []
            
            for cmd in template['commands']:
                if not self.config['dry_run']:
                    result = await self._run_command(cmd, timeout=300)
                    
                    if result['returncode'] != 0:
                        return f"Git installation failed at step: {cmd}\nError: {result['stderr']}"
                    
                    results.append(f"✓ {cmd}")
                else:
                    results.append(f"Dry run: {cmd}")
            
            # Post-installation
            if not self.config['dry_run'] and template.get('post_install'):
                await self._run_command(template['post_install'], timeout=60)
            
            # Verify
            if not self.config['dry_run']:
                verify_result = await self._run_command(template['verify'], timeout=10)
                if verify_result['returncode'] == 0:
                    self.stats['packages_installed'] += 1
                    return f"Git installed successfully: {verify_result['stdout'].strip()}\n" + '\n'.join(results)
                else:
                    return f"Git installation completed but verification failed"
            else:
                return f"Dry run: Would install Git\n" + '\n'.join(results)
                
        except Exception as e:
            self.stats['failed_installations'] += 1
            return f"Git installation error: {str(e)}"
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            'agent': self.name,
            'stats': self.stats,
            'config': self.config,
            'package_manager': self.primary_manager,
            'available_managers': self.package_managers,
            'install_templates': list(self.install_templates.keys())
        }


# Testing interface
if __name__ == "__main__":
    import asyncio
    
    # Mock objects for testing
    class MockSecurityManager:
        def can_execute_task(self, task):
            return True
        
        def log_agent_activity(self, agent, action, details):
            print(f"AUDIT: {agent} - {action} - {details}")
    
    class MockTask:
        def __init__(self, command):
            self.task_id = "test-task"
            self.command = command
    
    async def test_agent():
        import logging
        
        logger = logging.getLogger("test")
        security_manager = MockSecurityManager()
        hardware_info = {"config": {}}
        
        agent = SoftwareInstallAgent(hardware_info, security_manager, logger)
        
        # Test various scenarios
        test_cases = [
            "install vim",
            "search python",
            "install docker",
            "install nodejs",
            "verify git",
            "list installed packages"
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case}")
            task = MockTask(test_case)
            result = await agent.execute_task(task)
            print(f"Result: {result}")
    
    asyncio.run(test_agent()) 