#!/usr/bin/env python3
"""
Troubleshooting Agent - AI-powered system diagnostics and auto-fixing
"""

import asyncio
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import psutil
import logging

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent


class SystemDiagnostics:
    """System diagnostics data structure"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.disk_usage = 0.0
        self.network_status = "unknown"
        self.running_processes = []
        self.system_logs = []
        self.error_patterns = []
        self.hardware_issues = []
        self.service_status = {}
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'network_status': self.network_status,
            'running_processes': self.running_processes,
            'system_logs': self.system_logs,
            'error_patterns': self.error_patterns,
            'hardware_issues': self.hardware_issues,
            'service_status': self.service_status
        }


class TroubleshootingAgent(BaseAgent):
    """Agent for system troubleshooting and auto-fixing"""
    
    def __init__(self, hardware_info: Dict, security_manager, logger):
        super().__init__("troubleshooting_agent", hardware_info, security_manager, logger)
        self.name = "Troubleshooting Agent"
        self.description = "Diagnoses system issues and suggests automated fixes"
        
        # Troubleshooting configuration
        self.config = {
            "auto_fix_enabled": True,
            "safe_fixes_only": True,
            "max_fix_attempts": 3,
            "log_analysis_depth": 100,
            "network_timeout": 10,
            "service_check_timeout": 5
        }
        
        # Common error patterns and their fixes
        self.error_patterns = {
            # Network issues
            r"network.*unreachable|connection.*refused|no route to host": {
                "category": "network",
                "description": "Network connectivity issue",
                "fixes": [
                    "nmcli networking off && nmcli networking on",
                    "sudo systemctl restart NetworkManager",
                    "sudo dhclient -r && sudo dhclient"
                ]
            },
            
            # DNS issues
            r"dns.*resolution.*failed|name.*not.*resolved": {
                "category": "dns",
                "description": "DNS resolution failure",
                "fixes": [
                    "sudo systemctl restart systemd-resolved",
                    "sudo systemctl restart NetworkManager",
                    "echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf"
                ]
            },
            
            # Disk space issues
            r"no space left on device|disk.*full": {
                "category": "disk",
                "description": "Disk space exhausted",
                "fixes": [
                    "sudo apt autoremove -y",
                    "sudo apt autoclean",
                    "sudo journalctl --vacuum-time=7d"
                ]
            },
            
            # Memory issues
            r"out of memory|memory.*exhausted|cannot allocate memory": {
                "category": "memory",
                "description": "Memory exhaustion",
                "fixes": [
                    "sudo sync && sudo sysctl vm.drop_caches=3",
                    "sudo systemctl restart systemd-logind",
                    "pkill -f 'chrome|firefox' || true"
                ]
            },
            
            # Service issues
            r"service.*failed|unit.*failed|systemd.*failed": {
                "category": "service",
                "description": "Service failure",
                "fixes": [
                    "sudo systemctl daemon-reload",
                    "sudo systemctl reset-failed",
                    "sudo systemctl restart {service}"
                ]
            },
            
            # Package manager issues
            r"dpkg.*interrupted|apt.*lock|package.*broken": {
                "category": "package",
                "description": "Package manager issue",
                "fixes": [
                    "sudo dpkg --configure -a",
                    "sudo apt --fix-broken install",
                    "sudo rm -f /var/lib/dpkg/lock*"
                ]
            },
            
            # Permission issues
            r"permission denied|access denied|operation not permitted": {
                "category": "permission",
                "description": "Permission or access issue",
                "fixes": [
                    "sudo chown -R $USER:$USER ~/.config",
                    "sudo chmod -R 755 ~/.local",
                    "sudo usermod -a -G sudo $USER"
                ]
            }
        }
        
        # System health checks
        self.health_checks = {
            "cpu": self._check_cpu_usage,
            "memory": self._check_memory_usage,
            "disk": self._check_disk_usage,
            "network": self._check_network_connectivity,
            "services": self._check_critical_services,
            "logs": self._check_system_logs,
            "processes": self._check_problematic_processes
        }
        
        # Critical services to monitor
        self.critical_services = [
            "NetworkManager",
            "systemd-resolved",
            "ssh",
            "cron",
            "systemd-logind",
            "dbus"
        ]
        
        self.logger.info("Troubleshooting Agent initialized")
    
    def _initialize_rule_patterns(self) -> Dict[str, callable]:
        """Initialize rule-based patterns for troubleshooting"""
        return {
            'diagnose': self._rule_diagnose_system,
            'fix': self._rule_fix_issue,
            'network': self._rule_check_network,
            'memory': self._rule_check_memory,
            'disk': self._rule_check_disk,
            'service': self._rule_check_service,
            'logs': self._rule_check_logs,
            'performance': self._rule_check_performance,
            'health': self._rule_system_health_check
        }
    
    async def _process_task_with_llm(self, task) -> Dict:
        """Process troubleshooting task using LLM"""
        try:
            # Gather system diagnostics
            diagnostics = await self._gather_system_diagnostics()
            
            # Create context for LLM
            context = {
                'system_info': diagnostics.to_dict(),
                'user_query': task.command,
                'error_patterns': list(self.error_patterns.keys()),
                'available_fixes': [pattern['description'] for pattern in self.error_patterns.values()]
            }
            
            prompt = f"""
You are a system troubleshooting expert. Analyze this system issue and provide a solution.

User Query: {task.command}

System Status:
- CPU Usage: {diagnostics.cpu_usage}%
- Memory Usage: {diagnostics.memory_usage}%
- Disk Usage: {diagnostics.disk_usage}%
- Network Status: {diagnostics.network_status}
- Error Patterns Found: {diagnostics.error_patterns}

Based on the system status and user query, provide:
1. Diagnosis of the issue
2. Recommended fix command (if safe)
3. Explanation of the fix
4. Risk level (low/medium/high)

Format your response as JSON with keys: diagnosis, fix_command, explanation, risk_level
"""
            
            response = await self.query_llm(prompt, context)
            
            if response:
                try:
                    # Try to parse JSON response
                    result = json.loads(response)
                    
                    # Validate fix command safety
                    if result.get('fix_command') and self._is_safe_command(result['fix_command']):
                        return {
                            'success': True,
                            'diagnosis': result.get('diagnosis', 'LLM provided diagnosis'),
                            'fix_command': result['fix_command'],
                            'explanation': result.get('explanation', 'LLM provided explanation'),
                            'risk_level': result.get('risk_level', 'medium'),
                            'method': 'llm'
                        }
                    else:
                        return {
                            'success': True,
                            'diagnosis': result.get('diagnosis', 'Issue diagnosed'),
                            'explanation': result.get('explanation', 'Fix deemed unsafe'),
                            'risk_level': 'high',
                            'method': 'llm'
                        }
                        
                except json.JSONDecodeError:
                    # Fallback to text response
                    return {
                        'success': True,
                        'diagnosis': response,
                        'method': 'llm'
                    }
            else:
                # Fallback to rules
                return await self._process_task_with_rules(task)
                
        except Exception as e:
            self.logger.error(f"LLM processing failed: {e}")
            return await self._process_task_with_rules(task)
    
    async def _process_task_with_rules(self, task) -> Dict:
        """Process troubleshooting task using rule-based approach"""
        try:
            # Gather system diagnostics
            diagnostics = await self._gather_system_diagnostics()
            
            # Check for known error patterns
            for pattern, fix_info in self.error_patterns.items():
                if re.search(pattern, task.command, re.IGNORECASE):
                    return {
                        'success': True,
                        'diagnosis': fix_info['description'],
                        'fix_command': fix_info['fixes'][0],  # Use first fix
                        'explanation': f"Detected {fix_info['category']} issue",
                        'risk_level': 'low',
                        'method': 'rules'
                    }
            
            # Run comprehensive health check
            health_results = await self._run_health_checks()
            
            # Find issues and suggest fixes
            issues = []
            fixes = []
            
            for check_name, result in health_results.items():
                if not result.get('healthy', True):
                    issues.append(f"{check_name}: {result.get('issue', 'Unknown issue')}")
                    if result.get('fix'):
                        fixes.append(result['fix'])
            
            if issues:
                return {
                    'success': True,
                    'diagnosis': f"Found {len(issues)} issues: {'; '.join(issues)}",
                    'fix_command': fixes[0] if fixes else None,
                    'explanation': f"Automated health check found issues",
                    'risk_level': 'medium',
                    'method': 'rules'
                }
            else:
                return {
                    'success': True,
                    'diagnosis': 'No obvious issues detected. System appears healthy.',
                    'explanation': 'Ran comprehensive health check',
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
        return "A system troubleshooting agent that diagnoses issues and suggests automated fixes"
    
    def _get_supported_operations(self) -> List[str]:
        """Get list of operations this agent supports"""
        return [
            'diagnose', 'fix', 'network', 'memory', 'disk', 
            'service', 'logs', 'performance', 'health'
        ]
    
    async def _gather_system_diagnostics(self) -> SystemDiagnostics:
        """Gather comprehensive system diagnostics"""
        diagnostics = SystemDiagnostics()
        
        try:
            # CPU usage
            diagnostics.cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            diagnostics.memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            diagnostics.disk_usage = (disk.used / disk.total) * 100
            
            # Network connectivity
            diagnostics.network_status = await self._check_network_connectivity()
            
            # Running processes (top 10 by CPU)
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            diagnostics.running_processes = sorted(
                processes, 
                key=lambda x: x.get('cpu_percent', 0), 
                reverse=True
            )[:10]
            
            # System logs (recent errors)
            diagnostics.system_logs = await self._get_recent_errors()
            
            # Check for error patterns in logs
            diagnostics.error_patterns = self._find_error_patterns(diagnostics.system_logs)
            
            # Service status
            diagnostics.service_status = await self._check_critical_services()
            
        except Exception as e:
            self.logger.error(f"Error gathering diagnostics: {e}")
        
        return diagnostics
    
    async def _check_network_connectivity(self) -> str:
        """Check network connectivity"""
        try:
            # Test local connectivity
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return "connected"
            else:
                return "disconnected"
                
        except Exception as e:
            self.logger.error(f"Network check failed: {e}")
            return "unknown"
    
    async def _get_recent_errors(self) -> List[str]:
        """Get recent error messages from system logs"""
        try:
            result = subprocess.run(
                ["journalctl", "-p", "err", "-n", "50", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.split('\n')[-20:]  # Last 20 lines
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting logs: {e}")
            return []
    
    def _find_error_patterns(self, logs: List[str]) -> List[str]:
        """Find known error patterns in logs"""
        found_patterns = []
        
        for log_line in logs:
            for pattern in self.error_patterns.keys():
                if re.search(pattern, log_line, re.IGNORECASE):
                    found_patterns.append(pattern)
        
        return list(set(found_patterns))  # Remove duplicates
    
    async def _check_critical_services(self) -> Dict[str, str]:
        """Check status of critical services"""
        service_status = {}
        
        for service in self.critical_services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                service_status[service] = result.stdout.strip()
                
            except Exception as e:
                service_status[service] = f"error: {e}"
        
        return service_status
    
    async def _run_health_checks(self) -> Dict[str, Dict]:
        """Run comprehensive health checks"""
        results = {}
        
        for check_name, check_func in self.health_checks.items():
            try:
                results[check_name] = await check_func()
            except Exception as e:
                results[check_name] = {
                    'healthy': False,
                    'issue': f"Health check failed: {e}",
                    'error': str(e)
                }
        
        return results
    
    async def _check_cpu_usage(self) -> Dict:
        """Check CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > 90:
            return {
                'healthy': False,
                'issue': f'High CPU usage: {cpu_percent}%',
                'fix': 'pkill -f "chrome|firefox" || true'
            }
        
        return {'healthy': True, 'value': cpu_percent}
    
    async def _check_memory_usage(self) -> Dict:
        """Check memory usage"""
        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            return {
                'healthy': False,
                'issue': f'High memory usage: {memory.percent}%',
                'fix': 'sudo sync && sudo sysctl vm.drop_caches=3'
            }
        
        return {'healthy': True, 'value': memory.percent}
    
    async def _check_disk_usage(self) -> Dict:
        """Check disk usage"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        if disk_percent > 90:
            return {
                'healthy': False,
                'issue': f'High disk usage: {disk_percent:.1f}%',
                'fix': 'sudo apt autoremove -y && sudo apt autoclean'
            }
        
        return {'healthy': True, 'value': disk_percent}
    
    async def _check_problematic_processes(self) -> Dict:
        """Check for problematic processes"""
        try:
            # Find processes using too much CPU or memory
            problematic = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cpu_percent'] > 50 or proc.info['memory_percent'] > 20:
                        problematic.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if problematic:
                return {
                    'healthy': False,
                    'issue': f'Found {len(problematic)} resource-intensive processes',
                    'processes': problematic
                }
            
            return {'healthy': True}
            
        except Exception as e:
            return {
                'healthy': False,
                'issue': f'Process check failed: {e}'
            }
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if a command is safe to execute"""
        dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'rm\s+/.*',
            r'dd\s+if=.*of=/dev/',
            r'mkfs\.',
            r'fdisk.*',
            r'format\s+',
            r'chmod\s+777\s+/',
            r'chown.*root.*/',
            r'sudo\s+rm\s+-rf\s+/',
            r':\(\)\{.*\|\&\}',  # Fork bomb
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False
        
        return True
    
    # Rule-based handlers
    async def _rule_diagnose_system(self) -> Dict:
        """Rule-based system diagnosis"""
        diagnostics = await self._gather_system_diagnostics()
        health_results = await self._run_health_checks()
        
        issues = []
        for check_name, result in health_results.items():
            if not result.get('healthy', True):
                issues.append(f"{check_name}: {result.get('issue', 'Unknown issue')}")
        
        if issues:
            return {
                'success': True,
                'diagnosis': f"Found {len(issues)} issues: {'; '.join(issues)}",
                'system_info': diagnostics.to_dict()
            }
        else:
            return {
                'success': True,
                'diagnosis': 'System appears healthy',
                'system_info': diagnostics.to_dict()
            }
    
    async def _rule_fix_issue(self) -> Dict:
        """Rule-based issue fixing"""
        health_results = await self._run_health_checks()
        
        fixes_applied = []
        for check_name, result in health_results.items():
            if not result.get('healthy', True) and result.get('fix'):
                fix_command = result['fix']
                if self._is_safe_command(fix_command):
                    fixes_applied.append(f"{check_name}: {fix_command}")
        
        if fixes_applied:
            return {
                'success': True,
                'diagnosis': f"Applied {len(fixes_applied)} fixes",
                'fixes': fixes_applied
            }
        else:
            return {
                'success': True,
                'diagnosis': 'No safe fixes available'
            }
    
    async def _rule_check_network(self) -> Dict:
        """Rule-based network check"""
        status = await self._check_network_connectivity()
        
        if status == "connected":
            return {
                'success': True,
                'diagnosis': 'Network connectivity is working'
            }
        else:
            return {
                'success': True,
                'diagnosis': 'Network connectivity issue detected',
                'fix_command': 'nmcli networking off && nmcli networking on'
            }
    
    async def _rule_check_memory(self) -> Dict:
        """Rule-based memory check"""
        result = await self._check_memory_usage()
        
        if result['healthy']:
            return {
                'success': True,
                'diagnosis': f"Memory usage is normal: {result['value']}%"
            }
        else:
            return {
                'success': True,
                'diagnosis': result['issue'],
                'fix_command': result.get('fix')
            }
    
    async def _rule_check_disk(self) -> Dict:
        """Rule-based disk check"""
        result = await self._check_disk_usage()
        
        if result['healthy']:
            return {
                'success': True,
                'diagnosis': f"Disk usage is normal: {result['value']:.1f}%"
            }
        else:
            return {
                'success': True,
                'diagnosis': result['issue'],
                'fix_command': result.get('fix')
            }
    
    async def _rule_check_service(self) -> Dict:
        """Rule-based service check"""
        services = await self._check_critical_services()
        
        failed_services = [name for name, status in services.items() if status != "active"]
        
        if failed_services:
            return {
                'success': True,
                'diagnosis': f"Failed services: {', '.join(failed_services)}",
                'fix_command': f"sudo systemctl restart {failed_services[0]}"
            }
        else:
            return {
                'success': True,
                'diagnosis': 'All critical services are running'
            }
    
    async def _rule_check_logs(self) -> Dict:
        """Rule-based log check"""
        logs = await self._get_recent_errors()
        patterns = self._find_error_patterns(logs)
        
        if patterns:
            return {
                'success': True,
                'diagnosis': f"Found error patterns in logs: {', '.join(patterns[:3])}",
                'recent_errors': logs[-5:]
            }
        else:
            return {
                'success': True,
                'diagnosis': 'No obvious error patterns in recent logs'
            }
    
    async def _rule_check_performance(self) -> Dict:
        """Rule-based performance check"""
        cpu_result = await self._check_cpu_usage()
        memory_result = await self._check_memory_usage()
        
        issues = []
        if not cpu_result['healthy']:
            issues.append(f"CPU: {cpu_result['issue']}")
        if not memory_result['healthy']:
            issues.append(f"Memory: {memory_result['issue']}")
        
        if issues:
            return {
                'success': True,
                'diagnosis': f"Performance issues: {'; '.join(issues)}",
                'fix_command': cpu_result.get('fix') or memory_result.get('fix')
            }
        else:
            return {
                'success': True,
                'diagnosis': 'System performance is normal'
            }
    
    async def _rule_system_health_check(self) -> Dict:
        """Rule-based comprehensive health check"""
        return await self._rule_diagnose_system()


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
        logger = logging.getLogger("test")
        security_manager = MockSecurityManager()
        hardware_info = {"config": {}}
        
        agent = TroubleshootingAgent(hardware_info, security_manager, logger)
        
        # Test various scenarios
        test_cases = [
            "network not working",
            "system running slow",
            "disk space full",
            "service failed",
            "diagnose system"
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case}")
            task = MockTask(test_case)
            result = await agent.execute_task(task)
            print(f"Result: {result}")
    
    asyncio.run(test_agent()) 