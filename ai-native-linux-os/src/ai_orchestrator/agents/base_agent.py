#!/usr/bin/env python3
"""
Base Agent Class - Common functionality for all AI agents
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import uuid

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class AgentState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MessageType(Enum):
    TASK = "task"
    QUERY = "query"
    NOTIFICATION = "notification"
    HEALTH_CHECK = "health_check"


class AgentMessage:
    def __init__(self, msg_type: MessageType, content: Dict, sender: str = "system"):
        self.id = str(uuid.uuid4())
        self.type = msg_type
        self.content = content
        self.sender = sender
        self.timestamp = time.time()
        self.processed = False
        self.response = None


class BaseAgent(ABC):
    """Abstract base class for all AI agents"""
    
    def __init__(self, agent_name: str, hardware_info: Dict, 
                 security_manager, logger: logging.Logger):
        self.agent_name = agent_name
        self.hardware_info = hardware_info
        self.security_manager = security_manager
        self.logger = logger
        
        # Agent state
        self.state = AgentState.IDLE
        self.current_task = None
        self.task_history = []
        
        # LLM configuration
        self.llm_config = self._get_llm_config()
        self.model_name = self.llm_config.get('model', 'rule-based')
        self.use_llm = self.model_name != 'rule-based' and OLLAMA_AVAILABLE
        
        # Performance tracking
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0.0,
            'average_response_time': 0.0,
            'last_activity': time.time()
        }
        
        # Rule-based fallback system
        self.rule_patterns = self._initialize_rule_patterns()
        
        self.logger.info(f"{self.agent_name} initialized with model: {self.model_name}")
    
    def _get_llm_config(self) -> Dict:
        """Get LLM configuration for this agent"""
        agent_configs = self.hardware_info.get('llm_config', {}).get('agent_configs', {})
        return agent_configs.get(self.agent_name, {
            'level': 'FALLBACK',
            'model': 'rule-based',
            'use_gpu': False,
            'max_context_length': 512,
            'temperature': 0.3,
            'fallback_to_rules': True
        })
    
    @abstractmethod
    def _initialize_rule_patterns(self) -> Dict[str, Callable]:
        """Initialize rule-based patterns for fallback behavior"""
        pass
    
    @abstractmethod
    async def _process_task_with_llm(self, task: Any) -> Dict:
        """Process task using LLM (agent-specific implementation)"""
        pass
    
    @abstractmethod
    async def _process_task_with_rules(self, task: Any) -> Dict:
        """Process task using rule-based approach (agent-specific implementation)"""
        pass
    
    async def execute_task(self, task: Any) -> Dict:
        """Main task execution method"""
        start_time = time.time()
        self.current_task = task
        self.state = AgentState.PROCESSING
        
        try:
            # Security check
            if not self.security_manager.can_execute_task(task):
                raise SecurityError(f"Task blocked by security manager: {task.command}")
            
            # Log task start
            self.security_manager.log_agent_activity(
                self.agent_name, 
                "task_started", 
                {"task_id": task.task_id, "command": task.command}
            )
            
            # Choose processing method
            if self.use_llm and not self.llm_config.get('fallback_to_rules', False):
                try:
                    result = await self._process_task_with_llm(task)
                except Exception as e:
                    self.logger.warning(f"LLM processing failed, falling back to rules: {e}")
                    result = await self._process_task_with_rules(task)
            else:
                result = await self._process_task_with_rules(task)
            
            # Update statistics
            execution_time = time.time() - start_time
            self.stats['tasks_completed'] += 1
            self.stats['total_execution_time'] += execution_time
            self.stats['average_response_time'] = (
                self.stats['total_execution_time'] / self.stats['tasks_completed']
            )
            self.stats['last_activity'] = time.time()
            
            # Log success
            self.security_manager.log_agent_activity(
                self.agent_name,
                "task_completed",
                {
                    "task_id": task.task_id,
                    "execution_time": execution_time,
                    "success": True
                }
            )
            
            self.state = AgentState.IDLE
            return result
            
        except Exception as e:
            # Handle errors
            execution_time = time.time() - start_time
            self.stats['tasks_failed'] += 1
            self.state = AgentState.ERROR
            
            self.logger.error(f"Task execution failed: {e}")
            self.security_manager.log_agent_activity(
                self.agent_name,
                "task_failed",
                {
                    "task_id": task.task_id,
                    "error": str(e),
                    "execution_time": execution_time
                }
            )
            
            return {
                'success': False,
                'error': str(e),
                'agent': self.agent_name,
                'execution_time': execution_time
            }
        finally:
            self.current_task = None
    
    async def query_llm(self, prompt: str, context: Dict = None) -> Optional[str]:
        """Query the LLM with proper error handling"""
        if not self.use_llm:
            return None
        
        try:
            # Prepare context
            full_prompt = self._prepare_prompt(prompt, context)
            
            # Query LLM
            response = ollama.generate(
                model=self.model_name,
                prompt=full_prompt,
                options={
                    'temperature': self.llm_config.get('temperature', 0.3),
                    'num_ctx': self.llm_config.get('max_context_length', 2048)
                },
                stream=False
            )
            
            return response['response'].strip()
            
        except Exception as e:
            self.logger.error(f"LLM query failed: {e}")
            return None
    
    def _prepare_prompt(self, prompt: str, context: Dict = None) -> str:
        """Prepare prompt with context and agent-specific instructions"""
        base_prompt = f"""You are {self.agent_name}, a specialized AI agent in an AI-Native Linux OS.

Your role: {self._get_agent_description()}

Current context:
- Agent: {self.agent_name}
- Hardware Level: {self.llm_config.get('level', 'UNKNOWN')}
- Security: Enforced by security manager
- Current working directory: {context.get('cwd', '/') if context else '/'}

User request: {prompt}

Provide a specific, actionable response. Be concise and accurate."""

        return base_prompt
    
    @abstractmethod
    def _get_agent_description(self) -> str:
        """Get agent-specific description for prompts"""
        pass
    
    def match_rule_pattern(self, input_text: str) -> Optional[Callable]:
        """Match input against rule patterns"""
        input_lower = input_text.lower()
        
        for pattern, handler in self.rule_patterns.items():
            if pattern in input_lower:
                return handler
        
        return None
    
    async def health_check(self) -> Dict:
        """Perform agent health check"""
        health_status = {
            'agent_name': self.agent_name,
            'state': self.state.value,
            'model': self.model_name,
            'llm_available': self.use_llm,
            'last_activity': self.stats['last_activity'],
            'tasks_completed': self.stats['tasks_completed'],
            'tasks_failed': self.stats['tasks_failed'],
            'average_response_time': self.stats['average_response_time'],
            'memory_usage': self._get_memory_usage(),
            'timestamp': time.time()
        }
        
        # Test LLM if available
        if self.use_llm:
            try:
                test_response = await self.query_llm("Health check - respond with 'OK'")
                health_status['llm_test'] = 'pass' if test_response else 'fail'
            except Exception as e:
                health_status['llm_test'] = f'error: {e}'
        
        return health_status
    
    def _get_memory_usage(self) -> Dict:
        """Get memory usage information"""
        try:
            import psutil
            process = psutil.Process()
            return {
                'rss_mb': process.memory_info().rss / 1024 / 1024,
                'vms_mb': process.memory_info().vms / 1024 / 1024,
                'percent': process.memory_percent()
            }
        except Exception:
            return {'error': 'unable to get memory info'}
    
    def get_capabilities(self) -> Dict:
        """Get agent capabilities and limitations"""
        return {
            'agent_name': self.agent_name,
            'model': self.model_name,
            'level': self.llm_config.get('level'),
            'can_use_llm': self.use_llm,
            'max_context_length': self.llm_config.get('max_context_length'),
            'temperature': self.llm_config.get('temperature'),
            'permissions': self._get_permissions_summary(),
            'supported_operations': self._get_supported_operations()
        }
    
    def _get_permissions_summary(self) -> Dict:
        """Get summary of agent permissions"""
        permissions = self.security_manager.agent_permissions.get(self.agent_name)
        if not permissions:
            return {}
        
        return {
            'system_commands': permissions.system_commands,
            'file_write': permissions.file_write,
            'network_access': permissions.network_access,
            'process_control': permissions.process_control
        }
    
    @abstractmethod
    def _get_supported_operations(self) -> List[str]:
        """Get list of operations this agent supports"""
        pass
    
    async def shutdown(self):
        """Graceful shutdown of the agent"""
        self.logger.info(f"Shutting down {self.agent_name}")
        self.state = AgentState.MAINTENANCE
        
        # Cancel current task if any
        if self.current_task:
            self.logger.warning(f"Cancelling current task: {self.current_task.task_id}")
        
        # Log shutdown
        self.security_manager.log_agent_activity(
            self.agent_name,
            "shutdown",
            {"stats": self.stats}
        )
    
    def __str__(self) -> str:
        return f"{self.agent_name}(model={self.model_name}, state={self.state.value})"
    
    def __repr__(self) -> str:
        return self.__str__()


class SecurityError(Exception):
    """Security-related error"""
    pass


class LLMError(Exception):
    """LLM-related error"""
    pass


# Utility functions for agents
def extract_command_from_text(text: str) -> str:
    """Extract shell command from LLM response"""
    lines = text.split('\n')
    
    # Look for common command indicators
    for line in lines:
        line = line.strip()
        if line.startswith('$') or line.startswith('#'):
            return line[1:].strip()
        elif line and not line.startswith(('```', 'To', 'This', 'The')):
            # Likely a command
            return line
    
    return text.strip()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    import re
    # Remove dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    # Limit length
    return sanitized[:255]


def parse_file_size(size_str: str) -> int:
    """Parse file size string (e.g., '10MB', '2.5GB') to bytes"""
    import re
    
    size_str = size_str.upper().strip()
    
    # Extract number and unit
    match = re.match(r'([0-9.]+)\s*([KMGT]?B?)', size_str)
    if not match:
        return 0
    
    number = float(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        '': 1,
        'B': 1,
        'K': 1024,
        'KB': 1024,
        'M': 1024**2,
        'MB': 1024**2,
        'G': 1024**3,
        'GB': 1024**3,
        'T': 1024**4,
        'TB': 1024**4
    }
    
    return int(number * multipliers.get(unit, 1))


# Testing interface
if __name__ == "__main__":
    # This would normally be imported, but for testing we'll create a simple implementation
    
    class TestAgent(BaseAgent):
        def _initialize_rule_patterns(self):
            return {
                'hello': lambda: "Hello! I'm a test agent.",
                'test': lambda: "Test successful!"
            }
        
        async def _process_task_with_llm(self, task):
            response = await self.query_llm(f"Process this task: {task.command}")
            return {'success': True, 'result': response, 'method': 'llm'}
        
        async def _process_task_with_rules(self, task):
            handler = self.match_rule_pattern(task.command)
            if handler:
                result = handler()
                return {'success': True, 'result': result, 'method': 'rules'}
            else:
                return {'success': False, 'error': 'No matching rule', 'method': 'rules'}
        
        def _get_agent_description(self):
            return "A test agent for demonstrating base functionality"
        
        def _get_supported_operations(self):
            return ['hello', 'test', 'demo']
    
    
    # Mock objects for testing
    class MockSecurityManager:
        def can_execute_task(self, task):
            return True
        
        def log_agent_activity(self, agent, action, details):
            print(f"AUDIT: {agent} - {action} - {details}")
        
        agent_permissions = {
            'test_agent': type('MockPermissions', (), {
                'system_commands': False,
                'file_write': True,
                'network_access': False,
                'process_control': False
            })()
        }
    
    
    class MockTask:
        def __init__(self, command):
            self.task_id = str(uuid.uuid4())
            self.command = command
    
    
    async def test_base_agent():
        import logging
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("TestAgent")
        
        # Create test agent
        hardware_info = {
            'llm_config': {
                'agent_configs': {
                    'test_agent': {
                        'level': 'LOW',
                        'model': 'rule-based',
                        'fallback_to_rules': True
                    }
                }
            }
        }
        
        security_manager = MockSecurityManager()
        agent = TestAgent('test_agent', hardware_info, security_manager, logger)
        
        print(f"Created agent: {agent}")
        print(f"Capabilities: {agent.get_capabilities()}")
        
        # Test task execution
        test_task = MockTask("hello world")
        result = await agent.execute_task(test_task)
        print(f"Task result: {result}")
        
        # Test health check
        health = await agent.health_check()
        print(f"Health check: {health}")
        
        await agent.shutdown()
    
    
    # Run test
    asyncio.run(test_base_agent())