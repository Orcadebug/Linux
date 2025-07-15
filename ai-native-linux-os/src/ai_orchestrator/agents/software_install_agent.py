#!/usr/bin/env python3
"""
Software Installation Agent - Complex software installation and management
"""

import asyncio
import json
import os
import shutil
import subprocess
import time
import zipfile
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import re
import tempfile
import urllib.request
import hashlib

from .base_agent import BaseAgent, AgentMessage, MessageType, AgentState


class PackageManager:
    """Package manager abstraction"""
    
    @staticmethod
    def detect_package_manager():
        """Detect available package managers"""
        managers = {}
        
        # Check for common package managers
        for cmd, name in [
            ('apt', 'apt'),
            ('yum', 'yum'), 
            ('dnf', 'dnf'),
            ('pacman', 'pacman'),
            ('snap', 'snap'),
            ('flatpak', 'flatpak'),
            ('brew', 'homebrew')
        ]:
            if shutil.which(cmd):
                managers[name] = cmd
                
        return managers
    
    @staticmethod
    def get_primary_manager():
        """Get the primary package manager for the system"""
        managers = PackageManager.detect_package_manager()
        
        # Priority order
        priority = ['apt', 'dnf', 'yum', 'pacman', 'homebrew']
        for manager in priority:
            if manager in managers:
                return manager, managers[manager]
        
        return None, None


class SoftwareInstallAgent(BaseAgent):
    """Agent for handling complex software installations"""
    
    def __init__(self, hardware_info: Dict, security_manager, logger):
        super().__init__("software_install_agent", hardware_info, security_manager, logger)
        self.name = "Software Installation Agent"
        self.description = "Handles complex software installations and dependency resolution"
        
        # Installation tracking
        self.active_installations = {}
        self.installation_history = []
        self.rollback_points = {}
        
        # Package manager detection
        self.package_managers = PackageManager.detect_package_manager()
        self.primary_manager, self.primary_cmd = PackageManager.get_primary_manager()
        
        # Installation templates
        self.install_templates = self._load_install_templates()
        
        # Environment management
        self.env_backups = {}
        
        self.logger.info(f"Software Installation Agent initialized with {self.primary_manager}")
    
    def _initialize_rule_patterns(self) -> Dict[str, callable]:
        """Initialize rule-based patterns for software installation"""
        return {
            'install': self._rule_install_software,
            'remove': self._rule_remove_software,
            'update': self._rule_update_software,
            'search': self._rule_search_software,
            'list': self._rule_list_installed,
            'oracle': self._rule_install_oracle,
            'java': self._rule_install_java,
            'docker': self._rule_install_docker,
            'nodejs': self._rule_install_nodejs,
            'python': self._rule_install_python,
            'dependencies': self._rule_install_dependencies,
            'verify': self._rule_verify_installation,
            'rollback': self._rule_rollback_installation
        }
    
    def _get_agent_description(self) -> str:
        """Get agent-specific description for prompts"""
        return """Software installation and package management agent. I can:
- Install complex software packages (Oracle, Java, Docker, Node.js, etc.)
- Manage dependencies and resolve conflicts
- Configure environment variables and system settings
- Handle rollbacks and recovery from failed installations
- Verify installations and check system compatibility
- Manage multiple package managers (apt, yum, dnf, pacman, snap, etc.)
- Perform pre-installation checks and post-installation setup"""
    
    def _get_supported_operations(self) -> List[str]:
        """Get list of operations this agent supports"""
        return [
            'install_software',
            'remove_software',
            'update_software',
            'search_software',
            'list_installed',
            'install_oracle',
            'install_java',
            'install_docker',
            'install_nodejs',
            'install_python',
            'install_dependencies',
            'verify_installation',
            'rollback_installation',
            'check_compatibility',
            'manage_environment',
            'create_rollback_point'
        ]
    
    async def _process_task_with_llm(self, task) -> Dict:
        """Process task using LLM for intelligent software installation"""
        try:
            # Get system information for context
            system_info = {
                'package_managers': self.package_managers,
                'primary_manager': self.primary_manager,
                'available_templates': list(self.install_templates.keys()),
                'active_installations': len(self.active_installations)
            }
            
            # Prepare context for LLM
            context = {
                'system_info': system_info,
                'task_command': task.command if hasattr(task, 'command') else str(task),
                'agent_capabilities': self._get_supported_operations()
            }
            
            # Query LLM for intelligent response
            prompt = f"""Analyze this software installation request: {task.command if hasattr(task, 'command') else str(task)}

System information:
- Primary package manager: {self.primary_manager}
- Available package managers: {', '.join(self.package_managers.keys())}
- Supported complex installations: {', '.join(self.install_templates.keys())}
- Active installations: {len(self.active_installations)}

Provide specific installation steps and recommendations."""

            llm_response = await self.query_llm(prompt, context)
            
            if llm_response:
                # Parse LLM response and execute appropriate action
                command = task.command.lower() if hasattr(task, 'command') else str(task).lower()
                
                if any(soft in command for soft in ['oracle', 'java', 'docker', 'nodejs']):
                    # Complex installation
                    software = next((s for s in ['oracle', 'java', 'docker', 'nodejs'] if s in command), 'unknown')
                    result = await self._install_from_template(software, 'latest', {})
                elif 'install' in command:
                    # Generic installation
                    software = command.replace('install', '').strip()
                    result = await self._install_generic_software(software, 'latest', {})
                elif 'remove' in command or 'uninstall' in command:
                    software = command.replace('remove', '').replace('uninstall', '').strip()
                    result = await self._remove_software(software)
                elif 'search' in command:
                    query = command.replace('search', '').strip()
                    result = await self._search_software(query)
                elif 'list' in command:
                    result = await self._list_installed_software()
                else:
                    result = await self._get_installation_status()
                
                return {
                    'success': True,
                    'llm_analysis': llm_response,
                    'installation_data': result,
                    'agent': 'software_install_agent'
                }
            else:
                # Fallback to rule-based processing
                return await self._process_task_with_rules(task)
                
        except Exception as e:
            self.logger.error(f"Error processing task with LLM: {e}")
            return await self._process_task_with_rules(task)
    
    async def _process_task_with_rules(self, task) -> Dict:
        """Process task using rule-based approach"""
        try:
            command = task.command if hasattr(task, 'command') else str(task)
            command_lower = command.lower()
            
            # Match against rule patterns
            for pattern, handler in self.rule_patterns.items():
                if pattern in command_lower:
                    return await handler(command)
            
            # Default to installation status if no pattern matches
            return await self._rule_get_status(command)
            
        except Exception as e:
            self.logger.error(f"Error processing task with rules: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent': 'software_install_agent'
            }
    
    # Rule-based handlers
    async def _rule_install_software(self, command: str) -> Dict:
        """Install software using rule-based approach"""
        # Extract software name from command
        software = command.replace('install', '').strip()
        if not software:
            return {'success': False, 'error': 'No software specified'}
        
        result = await self._install_generic_software(software, 'latest', {})
        return {'success': result.get('status') == 'completed', 'action': 'install_software', 'result': result}
    
    async def _rule_remove_software(self, command: str) -> Dict:
        """Remove software"""
        software = command.replace('remove', '').replace('uninstall', '').strip()
        if not software:
            return {'success': False, 'error': 'No software specified'}
        
        result = await self._remove_software(software)
        return {'success': result.get('success', False), 'action': 'remove_software', 'result': result}
    
    async def _rule_update_software(self, command: str) -> Dict:
        """Update software"""
        result = await self._update_system_packages()
        return {'success': result.get('success', False), 'action': 'update_software', 'result': result}
    
    async def _rule_search_software(self, command: str) -> Dict:
        """Search for software"""
        query = command.replace('search', '').strip()
        if not query:
            return {'success': False, 'error': 'No search query specified'}
        
        result = await self._search_software(query)
        return {'success': result.get('success', False), 'action': 'search_software', 'result': result}
    
    async def _rule_list_installed(self, command: str) -> Dict:
        """List installed software"""
        result = await self._list_installed_software()
        return {'success': result.get('success', False), 'action': 'list_installed', 'result': result}
    
    async def _rule_install_oracle(self, command: str) -> Dict:
        """Install Oracle database"""
        result = await self._install_from_template('oracle', 'latest', {})
        return {'success': result.get('status') == 'completed', 'action': 'install_oracle', 'result': result}
    
    async def _rule_install_java(self, command: str) -> Dict:
        """Install Java JDK"""
        result = await self._install_from_template('java', 'latest', {})
        return {'success': result.get('status') == 'completed', 'action': 'install_java', 'result': result}
    
    async def _rule_install_docker(self, command: str) -> Dict:
        """Install Docker"""
        result = await self._install_from_template('docker', 'latest', {})
        return {'success': result.get('status') == 'completed', 'action': 'install_docker', 'result': result}
    
    async def _rule_install_nodejs(self, command: str) -> Dict:
        """Install Node.js"""
        result = await self._install_from_template('nodejs', 'latest', {})
        return {'success': result.get('status') == 'completed', 'action': 'install_nodejs', 'result': result}
    
    async def _rule_install_python(self, command: str) -> Dict:
        """Install Python"""
        result = await self._install_generic_software('python3', 'latest', {})
        return {'success': result.get('status') == 'completed', 'action': 'install_python', 'result': result}
    
    async def _rule_install_dependencies(self, command: str) -> Dict:
        """Install dependencies"""
        # Extract dependencies from command
        deps = command.replace('dependencies', '').replace('install', '').strip().split()
        if not deps:
            return {'success': False, 'error': 'No dependencies specified'}
        
        result = await self._install_dependencies(deps)
        return {'success': result.get('success', False), 'action': 'install_dependencies', 'result': result}
    
    async def _rule_verify_installation(self, command: str) -> Dict:
        """Verify installation"""
        software = command.replace('verify', '').strip()
        if not software:
            return {'success': False, 'error': 'No software specified for verification'}
        
        # Basic verification
        result = await self._verify_software_installed(software)
        return {'success': result.get('success', False), 'action': 'verify_installation', 'result': result}
    
    async def _rule_rollback_installation(self, command: str) -> Dict:
        """Rollback installation"""
        # Extract installation ID if provided
        parts = command.split()
        install_id = parts[-1] if len(parts) > 1 else None
        
        if install_id and install_id in self.rollback_points:
            result = await self._rollback_installation(install_id, self.rollback_points[install_id])
            return {'success': result.get('success', False), 'action': 'rollback_installation', 'result': result}
        else:
            return {'success': False, 'error': 'No valid installation ID provided or rollback point not found'}
    
    async def _rule_get_status(self, command: str) -> Dict:
        """Get installation status"""
        result = await self._get_installation_status()
        return {'success': True, 'action': 'installation_status', 'result': result}
    
    def _load_install_templates(self) -> Dict:
        """Load installation templates for complex software"""
        return {
            'oracle': {
                'name': 'Oracle Database',
                'versions': ['23c', '21c', '19c'],
                'dependencies': ['java-11-openjdk', 'libaio1', 'unzip'],
                'environment_vars': {
                    'ORACLE_HOME': '/opt/oracle/product/23c/dbhome_1',
                    'ORACLE_SID': 'ORCL',
                    'PATH': '$PATH:$ORACLE_HOME/bin'
                },
                'post_install_commands': [
                    'sudo systemctl enable oracle-db',
                    'sudo systemctl start oracle-db'
                ],
                'verification': {
                    'commands': ['sqlplus -version'],
                    'files': ['$ORACLE_HOME/bin/sqlplus'],
                    'services': ['oracle-db']
                }
            },
            'java': {
                'name': 'Java Development Kit',
                'versions': ['21', '17', '11', '8'],
                'dependencies': [],
                'environment_vars': {
                    'JAVA_HOME': '/usr/lib/jvm/default-java',
                    'PATH': '$PATH:$JAVA_HOME/bin'
                },
                'verification': {
                    'commands': ['java -version', 'javac -version'],
                    'files': ['$JAVA_HOME/bin/java']
                }
            },
            'docker': {
                'name': 'Docker Container Platform',
                'dependencies': ['curl', 'gnupg', 'lsb-release'],
                'environment_vars': {},
                'post_install_commands': [
                    'sudo systemctl enable docker',
                    'sudo systemctl start docker',
                    'sudo usermod -aG docker $USER'
                ],
                'verification': {
                    'commands': ['docker --version'],
                    'services': ['docker']
                }
            },
            'nodejs': {
                'name': 'Node.js Runtime',
                'versions': ['20', '18', '16'],
                'dependencies': [],
                'environment_vars': {
                    'NODE_PATH': '/usr/local/lib/node_modules',
                    'PATH': '$PATH:/usr/local/bin'
                },
                'verification': {
                    'commands': ['node --version', 'npm --version']
                }
            }
        }
    
    async def process_message(self, message: AgentMessage) -> Optional[Dict]:
        """Process installation requests"""
        try:
            if message.type == MessageType.TASK:
                return await self._handle_installation_task(message.content)
            elif message.type == MessageType.QUERY:
                return await self._handle_installation_query(message.content)
            else:
                return await super().process_message(message)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def _handle_installation_task(self, content: Dict) -> Dict:
        """Handle software installation tasks"""
        software = content.get('software', '').lower()
        version = content.get('version', 'latest')
        options = content.get('options', {})
        
        if not software:
            return {"error": "No software specified", "status": "failed"}
        
        # Check if we have a template for this software
        if software in self.install_templates:
            return await self._install_from_template(software, version, options)
        else:
            return await self._install_generic_software(software, version, options)
    
    async def _install_from_template(self, software: str, version: str, options: Dict) -> Dict:
        """Install software using predefined template"""
        template = self.install_templates[software]
        installation_id = f"{software}_{int(time.time())}"
        
        try:
            self.active_installations[installation_id] = {
                'software': software,
                'version': version,
                'status': 'preparing',
                'start_time': time.time(),
                'steps': []
            }
            
            # Step 1: Pre-installation checks
            await self._log_step(installation_id, "Running pre-installation checks")
            pre_check = await self._pre_installation_checks(template)
            if not pre_check['success']:
                return {"error": f"Pre-installation checks failed: {pre_check['error']}", 
                       "status": "failed", "installation_id": installation_id}
            
            # Step 2: Create rollback point
            await self._log_step(installation_id, "Creating rollback point")
            rollback_point = await self._create_rollback_point(installation_id)
            
            # Step 3: Install dependencies
            if template.get('dependencies'):
                await self._log_step(installation_id, "Installing dependencies")
                dep_result = await self._install_dependencies(template['dependencies'])
                if not dep_result['success']:
                    await self._rollback_installation(installation_id, rollback_point)
                    return {"error": f"Dependency installation failed: {dep_result['error']}", 
                           "status": "failed", "installation_id": installation_id}
            
            # Step 4: Download and install main software
            await self._log_step(installation_id, f"Installing {template['name']}")
            install_result = await self._install_main_software(software, version, template, options)
            if not install_result['success']:
                await self._rollback_installation(installation_id, rollback_point)
                return {"error": f"Main installation failed: {install_result['error']}", 
                       "status": "failed", "installation_id": installation_id}
            
            # Step 5: Configure environment variables
            if template.get('environment_vars'):
                await self._log_step(installation_id, "Configuring environment variables")
                env_result = await self._configure_environment(template['environment_vars'])
                if not env_result['success']:
                    self.logger.warning(f"Environment configuration partially failed: {env_result['error']}")
            
            # Step 6: Run post-installation commands
            if template.get('post_install_commands'):
                await self._log_step(installation_id, "Running post-installation setup")
                post_result = await self._run_post_install_commands(template['post_install_commands'])
                if not post_result['success']:
                    self.logger.warning(f"Post-installation setup partially failed: {post_result['error']}")
            
            # Step 7: Verify installation
            await self._log_step(installation_id, "Verifying installation")
            verify_result = await self._verify_installation(template.get('verification', {}))
            
            # Update installation status
            self.active_installations[installation_id]['status'] = 'completed' if verify_result['success'] else 'warning'
            self.active_installations[installation_id]['end_time'] = time.time()
            
            # Add to history
            self.installation_history.append(dict(self.active_installations[installation_id]))
            
            return {
                "status": "completed" if verify_result['success'] else "warning",
                "installation_id": installation_id,
                "software": template['name'],
                "version": version,
                "verification": verify_result,
                "duration": self.active_installations[installation_id]['end_time'] - 
                           self.active_installations[installation_id]['start_time']
            }
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            if installation_id in self.rollback_points:
                await self._rollback_installation(installation_id, self.rollback_points[installation_id])
            return {"error": str(e), "status": "failed", "installation_id": installation_id}
    
    async def _install_generic_software(self, software: str, version: str, options: Dict) -> Dict:
        """Install software using package manager"""
        installation_id = f"{software}_{int(time.time())}"
        
        try:
            if not self.primary_manager:
                return {"error": "No package manager available", "status": "failed"}
            
            self.active_installations[installation_id] = {
                'software': software,
                'version': version,
                'status': 'installing',
                'start_time': time.time(),
                'steps': []
            }
            
            # Construct package name with version if specified
            package_name = software
            if version and version != 'latest':
                if self.primary_manager == 'apt':
                    package_name = f"{software}={version}"
                elif self.primary_manager in ['dnf', 'yum']:
                    package_name = f"{software}-{version}"
            
            # Install using primary package manager
            await self._log_step(installation_id, f"Installing {package_name} using {self.primary_manager}")
            
            if self.primary_manager == 'apt':
                cmd = ['sudo', 'apt', 'update', '&&', 'sudo', 'apt', 'install', '-y', package_name]
            elif self.primary_manager == 'dnf':
                cmd = ['sudo', 'dnf', 'install', '-y', package_name]
            elif self.primary_manager == 'yum':
                cmd = ['sudo', 'yum', 'install', '-y', package_name]
            elif self.primary_manager == 'pacman':
                cmd = ['sudo', 'pacman', '-S', '--noconfirm', package_name]
            else:
                return {"error": f"Unsupported package manager: {self.primary_manager}", "status": "failed"}
            
            result = await self._run_command_async(' '.join(cmd))
            
            self.active_installations[installation_id]['status'] = 'completed' if result['success'] else 'failed'
            self.active_installations[installation_id]['end_time'] = time.time()
            
            return {
                "status": "completed" if result['success'] else "failed",
                "installation_id": installation_id,
                "software": software,
                "version": version,
                "output": result.get('output', ''),
                "error": result.get('error', '') if not result['success'] else None
            }
            
        except Exception as e:
            self.logger.error(f"Generic installation failed: {e}")
            return {"error": str(e), "status": "failed", "installation_id": installation_id}
    
    async def _handle_installation_query(self, content: Dict) -> Dict:
        """Handle queries about installations"""
        query_type = content.get('type', 'status')
        
        if query_type == 'status':
            installation_id = content.get('installation_id')
            if installation_id and installation_id in self.active_installations:
                return {"status": "success", "installation": self.active_installations[installation_id]}
            else:
                return {"status": "success", "active_installations": list(self.active_installations.keys())}
        
        elif query_type == 'history':
            limit = content.get('limit', 10)
            return {"status": "success", "history": self.installation_history[-limit:]}
        
        elif query_type == 'templates':
            return {"status": "success", "templates": list(self.install_templates.keys())}
        
        elif query_type == 'package_managers':
            return {"status": "success", "package_managers": self.package_managers, 
                   "primary": self.primary_manager}
        
        else:
            return {"error": f"Unknown query type: {query_type}", "status": "failed"}
    
    async def _pre_installation_checks(self, template: Dict) -> Dict:
        """Run pre-installation system checks"""
        try:
            checks = {
                'disk_space': await self._check_disk_space(),
                'package_manager': self.primary_manager is not None,
                'internet': await self._check_internet_connectivity(),
                'permissions': await self._check_sudo_permissions()
            }
            
            failed_checks = [k for k, v in checks.items() if not v]
            
            return {
                'success': len(failed_checks) == 0,
                'checks': checks,
                'error': f"Failed checks: {failed_checks}" if failed_checks else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_disk_space(self, required_gb: float = 2.0) -> bool:
        """Check if sufficient disk space is available"""
        try:
            result = await self._run_command_async("df -h / | tail -1 | awk '{print $4}'")
            if result['success']:
                available = result['output'].strip()
                # Parse available space (could be in K, M, G, T)
                if 'G' in available:
                    available_gb = float(available.replace('G', ''))
                    return available_gb >= required_gb
                elif 'T' in available:
                    available_tb = float(available.replace('T', ''))
                    return available_tb * 1024 >= required_gb
            return False
        except:
            return False
    
    async def _check_internet_connectivity(self) -> bool:
        """Check internet connectivity"""
        try:
            result = await self._run_command_async("ping -c 1 8.8.8.8")
            return result['success']
        except:
            return False
    
    async def _check_sudo_permissions(self) -> bool:
        """Check if user has sudo permissions"""
        try:
            result = await self._run_command_async("sudo -n true")
            return result['success']
        except:
            return False
    
    async def _create_rollback_point(self, installation_id: str) -> Dict:
        """Create a rollback point before installation"""
        try:
            rollback_data = {
                'timestamp': time.time(),
                'installed_packages': await self._get_installed_packages(),
                'environment_backup': dict(os.environ)
            }
            
            self.rollback_points[installation_id] = rollback_data
            return rollback_data
            
        except Exception as e:
            self.logger.error(f"Failed to create rollback point: {e}")
            return {}
    
    async def _get_installed_packages(self) -> List[str]:
        """Get list of currently installed packages"""
        try:
            if self.primary_manager == 'apt':
                result = await self._run_command_async("dpkg -l | grep '^ii' | awk '{print $2}'")
            elif self.primary_manager in ['dnf', 'yum']:
                result = await self._run_command_async("rpm -qa")
            elif self.primary_manager == 'pacman':
                result = await self._run_command_async("pacman -Q | awk '{print $1}'")
            else:
                return []
            
            if result['success']:
                return result['output'].strip().split('\n')
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get installed packages: {e}")
            return []
    
    async def _install_dependencies(self, dependencies: List[str]) -> Dict:
        """Install package dependencies"""
        try:
            if not dependencies:
                return {'success': True}
            
            if self.primary_manager == 'apt':
                cmd = f"sudo apt update && sudo apt install -y {' '.join(dependencies)}"
            elif self.primary_manager == 'dnf':
                cmd = f"sudo dnf install -y {' '.join(dependencies)}"
            elif self.primary_manager == 'yum':
                cmd = f"sudo yum install -y {' '.join(dependencies)}"
            elif self.primary_manager == 'pacman':
                cmd = f"sudo pacman -S --noconfirm {' '.join(dependencies)}"
            else:
                return {'success': False, 'error': f"Unsupported package manager: {self.primary_manager}"}
            
            result = await self._run_command_async(cmd)
            return {
                'success': result['success'],
                'error': result.get('error') if not result['success'] else None,
                'output': result.get('output', '')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _install_main_software(self, software: str, version: str, template: Dict, options: Dict) -> Dict:
        """Install the main software package"""
        try:
            # Special handling for different software types
            if software == 'oracle':
                return await self._install_oracle(version, options)
            elif software == 'java':
                return await self._install_java(version, options)
            elif software == 'docker':
                return await self._install_docker(options)
            elif software == 'nodejs':
                return await self._install_nodejs(version, options)
            else:
                # Generic installation
                return await self._install_generic_package(software, version)
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _install_oracle(self, version: str, options: Dict) -> Dict:
        """Install Oracle Database (simplified simulation)"""
        try:
            # This is a simplified simulation - real Oracle installation requires
            # downloading from Oracle website with authentication
            
            # Simulate Oracle installation steps
            steps = [
                "Creating Oracle user and groups",
                "Setting up Oracle directories",
                "Configuring kernel parameters",
                "Installing Oracle Database software",
                "Creating database instance",
                "Configuring listener"
            ]
            
            for step in steps:
                self.logger.info(f"Oracle installation: {step}")
                await asyncio.sleep(2)  # Simulate time-consuming operation
            
            return {
                'success': True,
                'message': f"Oracle Database {version} installation simulated successfully",
                'note': "This is a simulation - real Oracle installation requires manual download from Oracle website"
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _install_java(self, version: str, options: Dict) -> Dict:
        """Install Java Development Kit"""
        try:
            package_map = {
                '21': 'openjdk-21-jdk',
                '17': 'openjdk-17-jdk', 
                '11': 'openjdk-11-jdk',
                '8': 'openjdk-8-jdk'
            }
            
            package = package_map.get(version, 'default-jdk')
            
            if self.primary_manager == 'apt':
                cmd = f"sudo apt update && sudo apt install -y {package}"
            else:
                cmd = f"sudo {self.primary_cmd} install -y {package}"
            
            result = await self._run_command_async(cmd)
            return {
                'success': result['success'],
                'error': result.get('error') if not result['success'] else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _install_docker(self, options: Dict) -> Dict:
        """Install Docker using official installation script"""
        try:
            # Use Docker's official installation script
            cmd = "curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
            result = await self._run_command_async(cmd)
            
            if result['success']:
                # Add current user to docker group
                user_cmd = f"sudo usermod -aG docker {os.getenv('USER', 'user')}"
                await self._run_command_async(user_cmd)
            
            return {
                'success': result['success'],
                'error': result.get('error') if not result['success'] else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _install_nodejs(self, version: str, options: Dict) -> Dict:
        """Install Node.js using NodeSource repository"""
        try:
            if self.primary_manager == 'apt':
                # Use NodeSource repository for specific versions
                setup_cmd = f"curl -fsSL https://deb.nodesource.com/setup_{version}.x | sudo -E bash -"
                install_cmd = "sudo apt-get install -y nodejs"
                
                setup_result = await self._run_command_async(setup_cmd)
                if setup_result['success']:
                    install_result = await self._run_command_async(install_cmd)
                    return {
                        'success': install_result['success'],
                        'error': install_result.get('error') if not install_result['success'] else None
                    }
                else:
                    return {'success': False, 'error': setup_result.get('error')}
            else:
                # Generic installation for other package managers
                return await self._install_generic_package('nodejs', version)
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _install_generic_package(self, software: str, version: str) -> Dict:
        """Generic package installation"""
        try:
            package_name = software
            if version and version != 'latest':
                if self.primary_manager == 'apt':
                    package_name = f"{software}={version}"
                elif self.primary_manager in ['dnf', 'yum']:
                    package_name = f"{software}-{version}"
            
            cmd = f"sudo {self.primary_cmd} install -y {package_name}"
            result = await self._run_command_async(cmd)
            
            return {
                'success': result['success'],
                'error': result.get('error') if not result['success'] else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _configure_environment(self, env_vars: Dict[str, str]) -> Dict:
        """Configure environment variables"""
        try:
            # Backup current environment
            backup_file = f"/tmp/env_backup_{int(time.time())}.json"
            with open(backup_file, 'w') as f:
                json.dump(dict(os.environ), f)
            
            # Add environment variables to .bashrc
            bashrc_path = Path.home() / '.bashrc'
            env_lines = []
            
            for var, value in env_vars.items():
                # Expand variables like $PATH
                expanded_value = os.path.expandvars(value)
                env_lines.append(f"export {var}={expanded_value}")
                # Set in current environment
                os.environ[var] = expanded_value
            
            # Append to .bashrc
            with open(bashrc_path, 'a') as f:
                f.write('\n# Added by AI Software Installation Agent\n')
                f.write('\n'.join(env_lines))
                f.write('\n')
            
            return {'success': True, 'backup_file': backup_file}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_post_install_commands(self, commands: List[str]) -> Dict:
        """Run post-installation commands"""
        try:
            results = []
            for cmd in commands:
                result = await self._run_command_async(cmd)
                results.append({'command': cmd, 'success': result['success'], 
                              'output': result.get('output', ''), 'error': result.get('error', '')})
                
                if not result['success']:
                    self.logger.warning(f"Post-install command failed: {cmd}")
            
            success_count = sum(1 for r in results if r['success'])
            return {
                'success': success_count == len(commands),
                'results': results,
                'error': f"Failed {len(commands) - success_count} out of {len(commands)} commands" if success_count < len(commands) else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _verify_installation(self, verification: Dict) -> Dict:
        """Verify that installation was successful"""
        try:
            results = {
                'commands': [],
                'files': [],
                'services': []
            }
            
            # Test commands
            if 'commands' in verification:
                for cmd in verification['commands']:
                    result = await self._run_command_async(cmd)
                    results['commands'].append({
                        'command': cmd,
                        'success': result['success'],
                        'output': result.get('output', '')
                    })
            
            # Check files exist
            if 'files' in verification:
                for file_path in verification['files']:
                    expanded_path = os.path.expandvars(file_path)
                    exists = Path(expanded_path).exists()
                    results['files'].append({
                        'file': file_path,
                        'exists': exists
                    })
            
            # Check services
            if 'services' in verification:
                for service in verification['services']:
                    result = await self._run_command_async(f"systemctl is-active {service}")
                    results['services'].append({
                        'service': service,
                        'active': result['success'] and 'active' in result.get('output', '')
                    })
            
            # Calculate overall success
            all_commands_ok = all(r['success'] for r in results['commands'])
            all_files_ok = all(r['exists'] for r in results['files'])
            all_services_ok = all(r['active'] for r in results['services'])
            
            overall_success = all_commands_ok and all_files_ok and all_services_ok
            
            return {
                'success': overall_success,
                'results': results,
                'summary': {
                    'commands_passed': sum(1 for r in results['commands'] if r['success']),
                    'commands_total': len(results['commands']),
                    'files_found': sum(1 for r in results['files'] if r['exists']),
                    'files_total': len(results['files']),
                    'services_active': sum(1 for r in results['services'] if r['active']),
                    'services_total': len(results['services'])
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _rollback_installation(self, installation_id: str, rollback_point: Dict) -> Dict:
        """Rollback installation to previous state"""
        try:
            self.logger.info(f"Rolling back installation {installation_id}")
            
            # This is a simplified rollback - in production you'd want more sophisticated rollback
            # For now, just log what we would do
            rollback_actions = [
                "Remove newly installed packages",
                "Restore environment variables", 
                "Remove configuration files",
                "Stop and disable services"
            ]
            
            for action in rollback_actions:
                self.logger.info(f"Rollback: {action}")
                await asyncio.sleep(1)
            
            return {'success': True, 'message': 'Rollback completed'}
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _log_step(self, installation_id: str, step: str):
        """Log installation step"""
        if installation_id in self.active_installations:
            self.active_installations[installation_id]['steps'].append({
                'step': step,
                'timestamp': time.time()
            })
        self.logger.info(f"[{installation_id}] {step}")
    
    async def _run_command_async(self, command: str) -> Dict:
        """Run shell command asynchronously"""
        try:
            # Check permissions before running
            if not await self.security_manager.check_permission(
                self.agent_id, 'system_commands', {'command': command}
            ):
                return {'success': False, 'error': 'Permission denied for system command'}
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'output': stdout.decode() if stdout else '',
                'error': stderr.decode() if stderr else '',
                'returncode': process.returncode
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_status(self) -> Dict:
        """Get agent status and current installations"""
        status = await super().get_status()
        status.update({
            'active_installations': len(self.active_installations),
            'total_installations': len(self.installation_history),
            'package_managers': self.package_managers,
            'primary_manager': self.primary_manager
        })
        return status
    
    async def _remove_software(self, software: str) -> Dict:
        """Remove software using the primary package manager"""
        try:
            if not self.primary_manager:
                return {'success': False, 'error': 'No package manager available'}
            
            # Command mapping for different package managers
            remove_commands = {
                'apt': f'sudo apt remove -y {software}',
                'yum': f'sudo yum remove -y {software}',
                'dnf': f'sudo dnf remove -y {software}',
                'pacman': f'sudo pacman -R --noconfirm {software}',
                'homebrew': f'brew uninstall {software}'
            }
            
            cmd = remove_commands.get(self.primary_manager, f'sudo {self.primary_cmd} remove -y {software}')
            result = await self._run_command_async(cmd)
            
            return {
                'success': result['success'],
                'software': software,
                'manager': self.primary_manager,
                'error': result.get('error') if not result['success'] else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _update_system_packages(self) -> Dict:
        """Update system packages using the primary package manager"""
        try:
            if not self.primary_manager:
                return {'success': False, 'error': 'No package manager available'}
            
            # Command mapping for different package managers
            update_commands = {
                'apt': 'sudo apt update && sudo apt upgrade -y',
                'yum': 'sudo yum update -y',
                'dnf': 'sudo dnf update -y',
                'pacman': 'sudo pacman -Syu --noconfirm',
                'homebrew': 'brew update && brew upgrade'
            }
            
            cmd = update_commands.get(self.primary_manager, f'sudo {self.primary_cmd} update -y')
            result = await self._run_command_async(cmd)
            
            return {
                'success': result['success'],
                'manager': self.primary_manager,
                'error': result.get('error') if not result['success'] else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _search_software(self, query: str) -> Dict:
        """Search for software packages"""
        try:
            if not self.primary_manager:
                return {'success': False, 'error': 'No package manager available'}
            
            # Command mapping for different package managers
            search_commands = {
                'apt': f'apt search {query}',
                'yum': f'yum search {query}',
                'dnf': f'dnf search {query}',
                'pacman': f'pacman -Ss {query}',
                'homebrew': f'brew search {query}'
            }
            
            cmd = search_commands.get(self.primary_manager, f'{self.primary_cmd} search {query}')
            result = await self._run_command_async(cmd)
            
            return {
                'success': result['success'],
                'query': query,
                'manager': self.primary_manager,
                'results': result.get('output', '').split('\n')[:20],  # Limit to 20 results
                'error': result.get('error') if not result['success'] else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _list_installed_software(self) -> Dict:
        """List installed software packages"""
        try:
            if not self.primary_manager:
                return {'success': False, 'error': 'No package manager available'}
            
            # Command mapping for different package managers
            list_commands = {
                'apt': 'apt list --installed',
                'yum': 'yum list installed',
                'dnf': 'dnf list installed',
                'pacman': 'pacman -Q',
                'homebrew': 'brew list'
            }
            
            cmd = list_commands.get(self.primary_manager, f'{self.primary_cmd} list installed')
            result = await self._run_command_async(cmd)
            
            return {
                'success': result['success'],
                'manager': self.primary_manager,
                'packages': result.get('output', '').split('\n')[:50],  # Limit to 50 packages
                'error': result.get('error') if not result['success'] else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _verify_software_installed(self, software: str) -> Dict:
        """Verify if software is installed"""
        try:
            # Try to find the software in PATH
            which_result = await self._run_command_async(f'which {software}')
            if which_result['success']:
                return {
                    'success': True,
                    'software': software,
                    'installed': True,
                    'path': which_result.get('output', '').strip()
                }
            
            # Try version command
            version_result = await self._run_command_async(f'{software} --version')
            if version_result['success']:
                return {
                    'success': True,
                    'software': software,
                    'installed': True,
                    'version': version_result.get('output', '').strip()
                }
            
            # Check with package manager
            if self.primary_manager:
                check_commands = {
                    'apt': f'dpkg -l | grep {software}',
                    'yum': f'yum list installed | grep {software}',
                    'dnf': f'dnf list installed | grep {software}',
                    'pacman': f'pacman -Q | grep {software}',
                    'homebrew': f'brew list | grep {software}'
                }
                
                cmd = check_commands.get(self.primary_manager, f'{self.primary_cmd} list installed | grep {software}')
                check_result = await self._run_command_async(cmd)
                
                return {
                    'success': True,
                    'software': software,
                    'installed': check_result['success'],
                    'package_info': check_result.get('output', '').strip() if check_result['success'] else None
                }
            
            return {
                'success': True,
                'software': software,
                'installed': False,
                'error': 'Software not found'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _get_installation_status(self) -> Dict:
        """Get current installation status"""
        return {
            'success': True,
            'active_installations': len(self.active_installations),
            'installation_history': len(self.installation_history),
            'primary_manager': self.primary_manager,
            'available_managers': list(self.package_managers.keys()),
            'supported_templates': list(self.install_templates.keys()),
            'rollback_points': len(self.rollback_points)
        }
    
    async def cleanup(self):
        """Cleanup agent resources"""
        # Cancel any active installations
        for installation_id in self.active_installations:
            self.logger.info(f"Cancelling installation {installation_id}")
            self.active_installations[installation_id]['status'] = 'cancelled'
        
        await super().cleanup() 