#!/usr/bin/env python3
"""
Main AI Controller - Enhanced Orchestrator with specialized mixture of agents
Uses tiny LLMs and dormant behavior for efficient resource management
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
from collections import deque
from importlib import import_module

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .security_manager import SecurityManager
from .hardware_scanner import HardwareScanner

class MainAIController:
    """
    Main AI Controller with specialized mixture of agents architecture
    - Uses tiny LLMs for efficient classification and routing
    - Implements dormant agent behavior (lazy loading)
    - Supports multi-agent chaining for complex queries
    """
    
    def __init__(self):
        self.chat_history = deque(maxlen=10)  # Chat history for context (ChatGPT-like)
        self.central_model = "phi3:mini"  # Central tiny LLM for routing
        
        # Agent registry for lazy loading (dormant until needed)
        self.agent_registry = {
            'system_management': 'ai_orchestrator.agents.system_management_agent',
            'file_storage': 'ai_orchestrator.agents.file_storage_agent', 
            'media': 'ai_orchestrator.agents.media_agent',
            'communication': 'ai_orchestrator.agents.communication_agent',
            'personal_assistant': 'ai_orchestrator.agents.personal_assistant_agent',
            # Existing agents (adapted)
            'troubleshooting': 'ai_orchestrator.agents.troubleshooting_agent',
            'shell': 'ai_orchestrator.agents.shell_assistant_agent',
            'activity': 'ai_orchestrator.agents.activity_tracker_agent',
        }
        
        self.loaded_agents = {}  # Cache for loaded agents (dormant until used)
        self.security_manager = SecurityManager()
        self.hardware_scanner = HardwareScanner()
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Welcome message for ChatGPT-like interface
        self.welcome_message = """
🤖 Welcome to AI-Native Linux OS Hub!

I'm your intelligent OS assistant with specialized agents for:
• 🔧 System Management - Install software, update system, manage services
• 📁 File & Storage - Organize files, cleanup duplicates, manage storage
• 🎵 Media - Play music/videos, organize media library, convert formats
• 📧 Communication - Send emails, manage contacts, handle notifications
• 📅 Personal Assistant - Set reminders, manage schedule, track tasks
• 🔍 Troubleshooting - Diagnose issues, fix problems, monitor system
• 💻 Shell - Execute commands, manage processes, system operations
• 📊 Activity - Track usage, analyze patterns, generate insights

Ask me anything in natural language! Examples:
- "Organize my music folder"
- "Install Docker and start the service"
- "Set a reminder for my meeting tomorrow at 2 PM"
- "Check my email and send a reply"
- "What's taking up space on my disk?"

Each agent uses specialized tiny LLMs for efficient, focused processing.
"""
    
    async def classify_and_route(self, query: str) -> str:
        """
        Main routing function with mixture of agents architecture
        """
        try:
            # Add query to chat history for context
            self.chat_history.append(f"User: {query}")
            
            # Use central tiny LLM for initial classification
            if OLLAMA_AVAILABLE:
                classification_prompt = f"""
                Classify this query into one or more categories (can be multiple for complex queries):
                
                Categories:
                - system_management: Install/remove software, system updates, service management
                - file_storage: File organization, cleanup, storage analysis, backups
                - media: Media playback, library organization, format conversion
                - communication: Email, messages, calls, notifications, contacts
                - personal_assistant: Reminders, scheduling, tasks, information retrieval
                - troubleshooting: System diagnostics, error fixing, performance issues
                - shell: Command execution, process management, system operations
                - activity: Usage tracking, pattern analysis, system insights
                
                Chat history for context: {' '.join(list(self.chat_history)[-3:])}
                
                Current query: {query}
                
                Respond with categories separated by commas (e.g., "file_storage,personal_assistant")
                """
                
                try:
                    response = ollama.generate(model=self.central_model, prompt=classification_prompt)
                    categories = [cat.strip() for cat in response['response'].strip().lower().split(',')]
                except Exception as e:
                    self.logger.warning(f"LLM classification failed: {e}")
                    categories = [self._fallback_classify(query)]
            else:
                categories = [self._fallback_classify(query)]
            
            # Route to appropriate agents (mixture of agents)
            results = []
            for category in categories:
                if category in self.agent_registry:
                    try:
                        # Lazy load agent (dormant until now)
                        agent = await self._get_agent(category)
                        if agent:
                            result = await agent.handle(query)
                            results.append(f"[{category.replace('_', ' ').title()}] {result}")
                    except Exception as e:
                        self.logger.error(f"Error with {category} agent: {e}")
                        results.append(f"[{category.replace('_', ' ').title()}] Error: {str(e)}")
                else:
                    results.append(f"[Unknown] Category '{category}' not recognized")
            
            # Combine results from multiple agents
            if not results:
                results = ["I'm not sure how to help with that. Please try rephrasing your request."]
            
            combined_result = "\n\n".join(results)
            
            # Add response to chat history
            self.chat_history.append(f"AI: {combined_result}")
            
            return combined_result
            
        except Exception as e:
            self.logger.error(f"Error in classify_and_route: {e}")
            return f"Error processing request: {str(e)}"
    
    async def _get_agent(self, category: str):
        """
        Get agent instance with lazy loading (dormant behavior)
        """
        try:
            # Check if agent is already loaded
            if category in self.loaded_agents:
                return self.loaded_agents[category]
            
            # Lazy load the agent module
            module_path = self.agent_registry[category]
            module = import_module(module_path)
            
            # Create agent instance
            if hasattr(module, 'Agent'):
                agent_instance = module.Agent()
                self.loaded_agents[category] = agent_instance
                self.logger.info(f"Loaded dormant agent: {category}")
                return agent_instance
            else:
                self.logger.error(f"Agent class not found in {module_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading agent {category}: {e}")
            return None
    
    def _fallback_classify(self, query: str) -> str:
        """
        Fallback classification without LLM
        """
        query_lower = query.lower()
        
        # System management keywords
        if any(word in query_lower for word in ['install', 'update', 'service', 'package', 'system']):
            return 'system_management'
        
        # File storage keywords
        elif any(word in query_lower for word in ['organize', 'file', 'folder', 'storage', 'cleanup', 'duplicate']):
            return 'file_storage'
        
        # Media keywords
        elif any(word in query_lower for word in ['play', 'music', 'video', 'media', 'playlist']):
            return 'media'
        
        # Communication keywords
        elif any(word in query_lower for word in ['email', 'message', 'call', 'contact', 'notification']):
            return 'communication'
        
        # Personal assistant keywords
        elif any(word in query_lower for word in ['remind', 'schedule', 'appointment', 'task', 'weather', 'time']):
            return 'personal_assistant'
        
        # Troubleshooting keywords
        elif any(word in query_lower for word in ['fix', 'error', 'problem', 'diagnose', 'troubleshoot']):
            return 'troubleshooting'
        
        # Shell keywords
        elif any(word in query_lower for word in ['command', 'execute', 'run', 'process', 'terminal']):
            return 'shell'
        
        # Activity keywords
        elif any(word in query_lower for word in ['track', 'usage', 'activity', 'analysis', 'pattern']):
            return 'activity'
        
        else:
            return 'personal_assistant'  # Default to personal assistant
    
    def get_welcome_message(self) -> str:
        """Get welcome message for ChatGPT-like interface"""
        return self.welcome_message
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents (loaded/dormant)"""
        status = {
            'loaded_agents': list(self.loaded_agents.keys()),
            'dormant_agents': [agent for agent in self.agent_registry.keys() 
                             if agent not in self.loaded_agents],
            'total_agents': len(self.agent_registry),
            'memory_usage': f"{len(self.loaded_agents)}/{len(self.agent_registry)} agents loaded"
        }
        return status
    
    async def unload_agent(self, category: str):
        """
        Unload an agent to free memory (return to dormant state)
        """
        if category in self.loaded_agents:
            del self.loaded_agents[category]
            self.logger.info(f"Unloaded agent: {category} (returned to dormant state)")
    
    async def unload_all_agents(self):
        """
        Unload all agents to free memory
        """
        self.loaded_agents.clear()
        self.logger.info("All agents unloaded (returned to dormant state)")
    
    # CLI interface methods
    def run_cli(self):
        """Run the CLI interface"""
        print(self.get_welcome_message())
        
        while True:
            try:
                query = input("\n🤖 AI-Native OS > ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if query.lower() == 'status':
                    status = self.get_agent_status()
                    print(f"\n📊 Agent Status:")
                    print(f"• Loaded: {', '.join(status['loaded_agents']) if status['loaded_agents'] else 'None'}")
                    print(f"• Dormant: {', '.join(status['dormant_agents']) if status['dormant_agents'] else 'None'}")
                    print(f"• Memory: {status['memory_usage']}")
                    continue
                
                if query.lower() == 'help':
                    print(self.get_welcome_message())
                    continue
                
                # Process query asynchronously
                result = asyncio.run(self.classify_and_route(query))
                print(f"\n{result}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

# Main execution
if __name__ == "__main__":
    controller = MainAIController()
    controller.run_cli()