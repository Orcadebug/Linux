#!/usr/bin/env python3
"""
Main AI Controller - Orchestrates all specialized AI agents
"""

import asyncio
import json
import logging
import signal
import threading
import time
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, List, Optional, Any
import uuid

from .security_manager import SecurityManager
from .hardware_scanner import HardwareScanner
from .agents.system_agent import SystemAgent
from .agents.file_management_agent import FileManagementAgent
from .agents.software_install_agent import SoftwareInstallAgent
from .agents.shell_assistant_agent import ShellAssistantAgent
from .agents.activity_tracker_agent import ActivityTrackerAgent


class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    def __init__(self, task_id: str, agent_type: str, command: str, 
                 priority: TaskPriority = TaskPriority.MEDIUM, 
                 user_data: Dict = None):
        self.task_id = task_id
        self.agent_type = agent_type
        self.command = command
        self.priority = priority
        self.user_data = user_data or {}
        self.status = TaskStatus.PENDING
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None


class MainAIController:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize managers
        self.security_manager = SecurityManager(self.config.get("security", {}))
        self.hardware_scanner = HardwareScanner()
        
        # Agent management
        self.agents = {}
        self.agent_threads = {}
        self.task_queues = {}
        self.result_queue = Queue()
        
        # Task management
        self.tasks = {}
        self.task_history = []
        
        # Control flags
        self.running = False
        self.emergency_stop = False
        
        # Message routing
        self.message_router = {
            "system": "system_agent",
            "file": "file_management_agent", 
            "install": "software_install_agent",
            "shell": "shell_assistant_agent",
            "activity": "activity_tracker_agent"
        }
        
        self._setup_signal_handlers()
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "max_concurrent_tasks": 5,
            "task_timeout": 300,  # 5 minutes
            "log_level": "INFO",
            "security": {
                "require_confirmation": True,
                "dangerous_commands": ["rm -rf", "dd if=", "mkfs", "format", "fdisk"],
                "max_privilege_escalation": 1
            },
            "agents": {
                "system_agent": {"enabled": True, "max_tasks": 2},
                "file_management_agent": {"enabled": True, "max_tasks": 3},
                "software_install_agent": {"enabled": True, "max_tasks": 1},
                "shell_assistant_agent": {"enabled": True, "max_tasks": 2},
                "activity_tracker_agent": {"enabled": True, "max_tasks": 1}
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("MainAIController")
        logger.setLevel(getattr(logging, self.config.get("log_level", "INFO")))
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.emergency_stop_all()
    
    async def initialize(self):
        """Initialize all agents and start the controller"""
        try:
            self.logger.info("Initializing AI Controller...")
            
            # Scan hardware and determine capabilities
            hardware_info = await self.hardware_scanner.scan_system()
            self.logger.info(f"Hardware capabilities: {hardware_info}")
            
            # Initialize agents based on hardware capabilities
            await self._initialize_agents(hardware_info)
            
            # Start agent threads
            self._start_agent_threads()
            
            # Start main control loop
            self.running = True
            self.logger.info("AI Controller initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Controller: {e}")
            raise
    
    async def _initialize_agents(self, hardware_info: Dict):
        """Initialize all specialized agents"""
        agent_configs = self.config.get("agents", {})
        
        # System Agent
        if agent_configs.get("system_agent", {}).get("enabled", True):
            self.agents["system_agent"] = SystemAgent(
                hardware_info=hardware_info,
                security_manager=self.security_manager,
                logger=self.logger.getChild("SystemAgent")
            )
            self.task_queues["system_agent"] = Queue()
        
        # File Management Agent
        if agent_configs.get("file_management_agent", {}).get("enabled", True):
            self.agents["file_management_agent"] = FileManagementAgent(
                hardware_info=hardware_info,
                security_manager=self.security_manager,
                logger=self.logger.getChild("FileManagementAgent")
            )
            self.task_queues["file_management_agent"] = Queue()
        
        # Software Install Agent
        if agent_configs.get("software_install_agent", {}).get("enabled", True):
            self.agents["software_install_agent"] = SoftwareInstallAgent(
                hardware_info=hardware_info,
                security_manager=self.security_manager,
                logger=self.logger.getChild("SoftwareInstallAgent")
            )
            self.task_queues["software_install_agent"] = Queue()
        
        # Shell Assistant Agent
        if agent_configs.get("shell_assistant_agent", {}).get("enabled", True):
            self.agents["shell_assistant_agent"] = ShellAssistantAgent(
                hardware_info=hardware_info,
                security_manager=self.security_manager,
                logger=self.logger.getChild("ShellAssistantAgent")
            )
            self.task_queues["shell_assistant_agent"] = Queue()
        
        # Activity Tracker Agent
        if agent_configs.get("activity_tracker_agent", {}).get("enabled", True):
            self.agents["activity_tracker_agent"] = ActivityTrackerAgent(
                hardware_info=hardware_info,
                security_manager=self.security_manager,
                logger=self.logger.getChild("ActivityTrackerAgent")
            )
            self.task_queues["activity_tracker_agent"] = Queue()
        
        self.logger.info(f"Initialized {len(self.agents)} agents")
    
    def _start_agent_threads(self):
        """Start worker threads for each agent"""
        for agent_name, agent in self.agents.items():
            thread = threading.Thread(
                target=self._agent_worker,
                args=(agent_name, agent),
                daemon=True
            )
            thread.start()
            self.agent_threads[agent_name] = thread
            self.logger.info(f"Started thread for {agent_name}")
    
    def _agent_worker(self, agent_name: str, agent):
        """Worker thread for processing agent tasks"""
        queue = self.task_queues[agent_name]
        
        while self.running and not self.emergency_stop:
            try:
                # Get task from queue with timeout
                task = queue.get(timeout=1.0)
                
                if task is None:  # Shutdown signal
                    break
                
                self.logger.info(f"Processing task {task.task_id} with {agent_name}")
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()
                
                try:
                    # Execute task with timeout
                    result = asyncio.run(
                        asyncio.wait_for(
                            agent.execute_task(task),
                            timeout=self.config.get("task_timeout", 300)
                        )
                    )
                    
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = time.time()
                    
                    self.logger.info(f"Task {task.task_id} completed successfully")
                    
                except asyncio.TimeoutError:
                    task.error = "Task timeout"
                    task.status = TaskStatus.FAILED
                    self.logger.error(f"Task {task.task_id} timed out")
                    
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    self.logger.error(f"Task {task.task_id} failed: {e}")
                
                # Send result back
                self.result_queue.put(task)
                queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in agent worker {agent_name}: {e}")
    
    def route_task(self, user_input: str, context: Dict = None) -> str:
        """Route user input to appropriate agent and return task ID"""
        task_id = str(uuid.uuid4())
        
        # Determine which agent should handle the task
        agent_type = self._determine_agent(user_input, context)
        
        # Create task
        task = Task(
            task_id=task_id,
            agent_type=agent_type,
            command=user_input,
            user_data=context or {}
        )
        
        # Security check
        if not self.security_manager.can_execute_task(task):
            task.status = TaskStatus.FAILED
            task.error = "Security check failed"
            self.tasks[task_id] = task
            return task_id
        
        # Queue task
        if agent_type in self.task_queues:
            self.task_queues[agent_type].put(task)
            self.tasks[task_id] = task
            self.logger.info(f"Routed task {task_id} to {agent_type}")
        else:
            task.status = TaskStatus.FAILED
            task.error = f"Unknown agent type: {agent_type}"
            self.tasks[task_id] = task
        
        return task_id
    
    def _determine_agent(self, user_input: str, context: Dict = None) -> str:
        """Determine which agent should handle the user input"""
        input_lower = user_input.lower()
        
        # File operations
        if any(keyword in input_lower for keyword in [
            "organize", "cleanup", "download", "file", "folder", "directory"
        ]):
            return "file_management_agent"
        
        # Software installation
        if any(keyword in input_lower for keyword in [
            "install", "setup", "configure", "oracle", "java", "dependency"
        ]):
            return "software_install_agent"
        
        # System monitoring
        if any(keyword in input_lower for keyword in [
            "system", "monitor", "performance", "cpu", "memory", "disk"
        ]):
            return "system_agent"
        
        # Activity tracking
        if any(keyword in input_lower for keyword in [
            "history", "pattern", "activity", "usage", "workflow", "productivity"
        ]):
            return "activity_tracker_agent"
        
        # Default to shell assistant
        return "shell_assistant_agent"
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "agent_type": task.agent_type,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error
        }
    
    def get_all_tasks(self) -> List[Dict]:
        """Get status of all tasks"""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents"""
        status = {}
        for agent_name, agent in self.agents.items():
            queue = self.task_queues.get(agent_name)
            status[agent_name] = {
                "running": agent_name in self.agent_threads,
                "queue_size": queue.qsize() if queue else 0,
                "thread_alive": self.agent_threads.get(agent_name, {}).is_alive() if agent_name in self.agent_threads else False
            }
        return status
    
    def emergency_stop_all(self):
        """Emergency stop all agents and tasks"""
        self.logger.warning("EMERGENCY STOP ACTIVATED")
        self.emergency_stop = True
        self.running = False
        
        # Cancel all pending tasks
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING or task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.CANCELLED
                task.error = "Emergency stop activated"
        
        # Signal all agent threads to stop
        for queue in self.task_queues.values():
            queue.put(None)  # Shutdown signal
        
        # Wait for threads to stop
        for thread in self.agent_threads.values():
            thread.join(timeout=5.0)
        
        self.logger.info("Emergency stop completed")
    
    async def shutdown(self):
        """Graceful shutdown of the controller"""
        self.logger.info("Shutting down AI Controller...")
        self.running = False
        
        # Wait for current tasks to complete
        for queue in self.task_queues.values():
            queue.join()
        
        # Stop agent threads
        for queue in self.task_queues.values():
            queue.put(None)
        
        for thread in self.agent_threads.values():
            thread.join(timeout=10.0)
        
        self.logger.info("AI Controller shutdown complete")
    
    async def process_user_request(self, user_input: str, context: Dict = None) -> Dict:
        """Main entry point for processing user requests"""
        try:
            # Route task to appropriate agent
            task_id = self.route_task(user_input, context)
            
            # Wait for task completion or timeout
            start_time = time.time()
            timeout = self.config.get("task_timeout", 300)
            
            while time.time() - start_time < timeout:
                # Check for completed task
                try:
                    completed_task = self.result_queue.get(timeout=1.0)
                    if completed_task.task_id == task_id:
                        return {
                            "success": completed_task.status == TaskStatus.COMPLETED,
                            "result": completed_task.result,
                            "error": completed_task.error,
                            "agent_used": completed_task.agent_type,
                            "execution_time": completed_task.completed_at - completed_task.started_at if completed_task.completed_at else None
                        }
                except Empty:
                    continue
            
            # Timeout reached
            return {
                "success": False,
                "error": "Request timeout",
                "task_id": task_id
            }
            
        except Exception as e:
            self.logger.error(f"Error processing user request: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# CLI interface for testing
async def main():
    controller = MainAIController()
    
    try:
        await controller.initialize()
        
        print("🤖 AI-Native Linux OS Controller Started")
        print("Type 'help' for commands, 'quit' to exit, 'emergency' for emergency stop")
        
        while controller.running:
            try:
                user_input = input("\nAI> ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    break
                elif user_input.lower() == 'emergency':
                    controller.emergency_stop_all()
                    break
                elif user_input.lower() == 'status':
                    print(f"Agent Status: {controller.get_agent_status()}")
                    print(f"Active Tasks: {len([t for t in controller.tasks.values() if t.status == TaskStatus.IN_PROGRESS])}")
                    continue
                elif user_input.lower() == 'help':
                    print("""
Available commands:
- Any natural language request (routed to appropriate agent)
- 'status' - Show agent and task status
- 'emergency' - Emergency stop all agents
- 'quit' - Graceful shutdown
                    """)
                    continue
                
                if not user_input:
                    continue
                
                print("Processing request...")
                result = await controller.process_user_request(user_input)
                
                if result["success"]:
                    print(f"✅ Success ({result['agent_used']})")
                    if result["result"]:
                        print(f"Result: {result['result']}")
                else:
                    print(f"❌ Error: {result['error']}")
                    
            except (KeyboardInterrupt, EOFError):
                break
                
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())