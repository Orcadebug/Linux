#!/usr/bin/env python3
"""
Self-Healing Service - Automatic service recovery and restart capabilities
"""

import os
import sys
import time
import json
import logging
import psutil
import subprocess
import threading
import signal
from datetime import datetime, timedelta
from pathlib import Path


class SelfHealingService:
    def __init__(self, config_file=None):
        self.config = self.load_config(config_file)
        self.running = False
        self.service_states = {}
        self.restart_counts = {}
        self.setup_logging()
        self.setup_signal_handlers()
        
    def load_config(self, config_file):
        """Load configuration from file or use defaults"""
        default_config = {
            "services": [
                {
                    "name": "sshd",
                    "command": "systemctl start sshd",
                    "check_command": "systemctl is-active sshd",
                    "critical": True,
                    "max_restarts": 3,
                    "restart_delay": 30
                },
                {
                    "name": "nginx",
                    "command": "systemctl start nginx",
                    "check_command": "systemctl is-active nginx",
                    "critical": False,
                    "max_restarts": 5,
                    "restart_delay": 10
                },
                {
                    "name": "mysql",
                    "command": "systemctl start mysql",
                    "check_command": "systemctl is-active mysql",
                    "critical": True,
                    "max_restarts": 3,
                    "restart_delay": 60
                }
            ],
            "processes": [
                {
                    "name": "quest_log_daemon",
                    "command": "python3 /opt/ai-native-linux/src/quest_log/quest_log_daemon.py --daemon",
                    "pidfile": "/var/run/quest_log_daemon.pid",
                    "critical": True,
                    "max_restarts": 5,
                    "restart_delay": 5
                },
                {
                    "name": "kernel_monitor",
                    "command": "python3 /opt/ai-native-linux/src/kernel_monitor/kernel_monitor.py",
                    "pidfile": "/var/run/kernel_monitor.pid",
                    "critical": True,
                    "max_restarts": 5,
                    "restart_delay": 5
                }
            ],
            "check_interval": 30,
            "log_file": "/var/log/self_healing.log",
            "max_restart_window": 3600  # 1 hour
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['log_file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('SelfHealingService')
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def run_command(self, command, timeout=30):
        """Run a shell command with timeout"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {command}")
            return False, "", "Command timed out"
        except Exception as e:
            self.logger.error(f"Error running command '{command}': {e}")
            return False, "", str(e)
    
    def check_service_status(self, service):
        """Check if a systemd service is running"""
        success, stdout, stderr = self.run_command(service['check_command'])
        
        if success and "active" in stdout.lower():
            return True
        
        self.logger.warning(f"Service {service['name']} is not active")
        return False
    
    def check_process_status(self, process):
        """Check if a process is running"""
        if 'pidfile' in process and os.path.exists(process['pidfile']):
            try:
                with open(process['pidfile'], 'r') as f:
                    pid = int(f.read().strip())
                
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    if proc.is_running():
                        return True
            except:
                pass
        
        # Check by process name
        process_name = process['name']
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if process_name in proc.info['name'] or any(process_name in arg for arg in proc.info['cmdline']):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        self.logger.warning(f"Process {process['name']} is not running")
        return False
    
    def restart_service(self, service):
        """Restart a systemd service"""
        service_name = service['name']
        
        # Check restart limits
        now = datetime.now()
        if service_name not in self.restart_counts:
            self.restart_counts[service_name] = []
        
        # Remove old restart attempts outside the window
        window_start = now - timedelta(seconds=self.config['max_restart_window'])
        self.restart_counts[service_name] = [
            timestamp for timestamp in self.restart_counts[service_name]
            if timestamp > window_start
        ]
        
        # Check if we've exceeded max restarts
        if len(self.restart_counts[service_name]) >= service['max_restarts']:
            self.logger.error(f"Max restarts exceeded for service {service_name}")
            return False
        
        # Attempt restart
        self.logger.info(f"Restarting service {service_name}...")
        
        success, stdout, stderr = self.run_command(service['command'])
        
        if success:
            self.logger.info(f"Successfully restarted service {service_name}")
            self.restart_counts[service_name].append(now)
            
            # Log to quest log
            self.log_healing_action("service_restart", service_name, "success")
            
            # Wait for service to stabilize
            time.sleep(service.get('restart_delay', 10))
            return True
        else:
            self.logger.error(f"Failed to restart service {service_name}: {stderr}")
            self.log_healing_action("service_restart", service_name, "failure", stderr)
            return False
    
    def restart_process(self, process):
        """Restart a process"""
        process_name = process['name']
        
        # Check restart limits
        now = datetime.now()
        if process_name not in self.restart_counts:
            self.restart_counts[process_name] = []
        
        # Remove old restart attempts outside the window
        window_start = now - timedelta(seconds=self.config['max_restart_window'])
        self.restart_counts[process_name] = [
            timestamp for timestamp in self.restart_counts[process_name]
            if timestamp > window_start
        ]
        
        # Check if we've exceeded max restarts
        if len(self.restart_counts[process_name]) >= process['max_restarts']:
            self.logger.error(f"Max restarts exceeded for process {process_name}")
            return False
        
        # Kill existing process if it exists
        self.kill_process(process_name)
        
        # Wait a moment
        time.sleep(2)
        
        # Start the process
        self.logger.info(f"Starting process {process_name}...")
        
        try:
            # Run process in background
            proc = subprocess.Popen(
                process['command'],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Save PID if pidfile is specified
            if 'pidfile' in process:
                with open(process['pidfile'], 'w') as f:
                    f.write(str(proc.pid))
            
            self.logger.info(f"Successfully started process {process_name} (PID: {proc.pid})")
            self.restart_counts[process_name].append(now)
            
            # Log to quest log
            self.log_healing_action("process_restart", process_name, "success")
            
            # Wait for process to stabilize
            time.sleep(process.get('restart_delay', 5))
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start process {process_name}: {e}")
            self.log_healing_action("process_restart", process_name, "failure", str(e))
            return False
    
    def kill_process(self, process_name):
        """Kill a process by name"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if process_name in proc.info['name'] or any(process_name in arg for arg in proc.info['cmdline']):
                    proc.terminate()
                    proc.wait(timeout=10)
                    self.logger.info(f"Terminated process {process_name} (PID: {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
    
    def log_healing_action(self, action_type, target, status, error=None):
        """Log healing action to quest log"""
        try:
            healing_log_file = Path.home() / ".self_healing_actions.json"
            
            action_data = {
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'target': target,
                'status': status,
                'error': error
            }
            
            actions_history = []
            if healing_log_file.exists():
                try:
                    with open(healing_log_file, 'r') as f:
                        actions_history = json.load(f)
                except:
                    actions_history = []
            
            actions_history.append(action_data)
            
            # Keep only recent actions
            if len(actions_history) > 1000:
                actions_history = actions_history[-1000:]
            
            with open(healing_log_file, 'w') as f:
                json.dump(actions_history, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Error logging healing action: {e}")
    
    def monitor_services(self):
        """Monitor systemd services"""
        for service in self.config['services']:
            try:
                if not self.check_service_status(service):
                    self.logger.warning(f"Service {service['name']} is down, attempting restart...")
                    self.restart_service(service)
            except Exception as e:
                self.logger.error(f"Error monitoring service {service['name']}: {e}")
    
    def monitor_processes(self):
        """Monitor custom processes"""
        for process in self.config['processes']:
            try:
                if not self.check_process_status(process):
                    self.logger.warning(f"Process {process['name']} is down, attempting restart...")
                    self.restart_process(process)
            except Exception as e:
                self.logger.error(f"Error monitoring process {process['name']}: {e}")
    
    def start(self):
        """Start the self-healing service"""
        self.logger.info("Starting Self-Healing Service...")
        self.running = True
        
        while self.running:
            try:
                # Monitor services
                self.monitor_services()
                
                # Monitor processes
                self.monitor_processes()
                
                # Wait for next check
                time.sleep(self.config['check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
        
        self.logger.info("Self-Healing Service stopped")


def main():
    """Main entry point"""
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    service = SelfHealingService(config_file)
    service.start()


if __name__ == '__main__':
    main()