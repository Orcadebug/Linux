#!/usr/bin/env python3
"""
Personal Assistant Agent - Handles reminders, scheduling, and information retrieval
Uses tiny LLM for efficient, domain-specific processing
"""

import asyncio
import os
import subprocess
import logging
import json
import datetime
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
import calendar

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent

class PersonalAssistantAgent(BaseAgent):
    """
    Specialized agent for personal assistance tasks
    - Reminder management
    - Schedule management
    - Information retrieval
    - Task tracking
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "PersonalAssistant"
        self.tiny_model = "phi3:mini"  # Tiny LLM for this domain
        self.capabilities = [
            "set_reminder",
            "manage_schedule",
            "get_information",
            "track_tasks",
            "weather_info",
            "time_management"
        ]
        self.data_dir = os.path.expanduser("~/.local/share/ai-native-linux/assistant")
        self.reminders_file = os.path.join(self.data_dir, "reminders.json")
        self.schedule_file = os.path.join(self.data_dir, "schedule.json")
        self.tasks_file = os.path.join(self.data_dir, "tasks.json")
        
        # Create data directory
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize data files
        self.reminders = self._load_json_file(self.reminders_file, [])
        self.schedule = self._load_json_file(self.schedule_file, {})
        self.tasks = self._load_json_file(self.tasks_file, [])
        
    def _load_json_file(self, filepath: str, default: Any) -> Any:
        """Load JSON file with default fallback"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Could not load {filepath}: {e}")
        return default
    
    def _save_json_file(self, filepath: str, data: Any):
        """Save data to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Could not save {filepath}: {e}")
    
    async def handle(self, query: str) -> str:
        """Handle personal assistant queries with tiny LLM"""
        try:
            # Use tiny LLM for domain-specific classification
            if OLLAMA_AVAILABLE:
                classification_prompt = f"""
                Classify this personal assistant query into one category:
                - reminder: Set, list, or manage reminders
                - schedule: Manage calendar and appointments
                - info: Get information (weather, news, facts)
                - task: Track tasks and to-dos
                - time: Time-related queries
                - search: Search for information
                
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
            if category == 'reminder':
                return await self._handle_reminder(query)
            elif category == 'schedule':
                return await self._handle_schedule(query)
            elif category == 'info':
                return await self._handle_info(query)
            elif category == 'task':
                return await self._handle_task(query)
            elif category == 'time':
                return await self._handle_time(query)
            elif category == 'search':
                return await self._handle_search(query)
            else:
                return await self._handle_general(query)
                
        except Exception as e:
            logging.error(f"PersonalAssistantAgent error: {e}")
            return f"Error processing personal assistant request: {str(e)}"
    
    def _fallback_classify(self, query: str) -> str:
        """Fallback classification without LLM"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['remind', 'reminder', 'alert']):
            return 'reminder'
        elif any(word in query_lower for word in ['schedule', 'appointment', 'meeting', 'calendar']):
            return 'schedule'
        elif any(word in query_lower for word in ['weather', 'news', 'information', 'what is']):
            return 'info'
        elif any(word in query_lower for word in ['task', 'todo', 'to-do', 'list']):
            return 'task'
        elif any(word in query_lower for word in ['time', 'date', 'today', 'tomorrow']):
            return 'time'
        elif any(word in query_lower for word in ['search', 'find', 'look up']):
            return 'search'
        else:
            return 'general'
    
    async def _handle_reminder(self, query: str) -> str:
        """Handle reminder operations"""
        try:
            if "set" in query.lower() or "add" in query.lower():
                return await self._set_reminder(query)
            elif "list" in query.lower() or "show" in query.lower():
                return await self._list_reminders()
            elif "delete" in query.lower() or "remove" in query.lower():
                return await self._delete_reminder(query)
            else:
                return "🔔 Reminder options: set reminder, list reminders, delete reminder"
                
        except Exception as e:
            return f"Error handling reminder: {str(e)}"
    
    async def _set_reminder(self, query: str) -> str:
        """Set a new reminder"""
        try:
            # Extract reminder details using LLM
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the reminder text and time from this request:
                "{query}"
                
                Respond in format: "reminder_text:time" (e.g., "Meeting with John:2024-01-15 14:00")
                If no specific time is mentioned, use "reminder_text:soon"
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                parts = response['response'].strip().split(':')
                if len(parts) >= 2:
                    reminder_text = parts[0]
                    time_str = ':'.join(parts[1:])
                else:
                    return "Please specify what to remind you about."
            else:
                # Simple extraction
                reminder_text = query.replace("set reminder", "").replace("remind me", "").strip()
                time_str = "soon"
            
            # Parse time
            reminder_time = None
            if time_str != "soon":
                try:
                    reminder_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                except:
                    try:
                        reminder_time = datetime.datetime.strptime(time_str, "%H:%M")
                        reminder_time = reminder_time.replace(
                            year=datetime.datetime.now().year,
                            month=datetime.datetime.now().month,
                            day=datetime.datetime.now().day
                        )
                    except:
                        reminder_time = None
            
            # Create reminder
            reminder = {
                "id": len(self.reminders) + 1,
                "text": reminder_text,
                "time": reminder_time.isoformat() if reminder_time else None,
                "created": datetime.datetime.now().isoformat(),
                "completed": False
            }
            
            self.reminders.append(reminder)
            self._save_json_file(self.reminders_file, self.reminders)
            
            time_display = reminder_time.strftime("%Y-%m-%d %H:%M") if reminder_time else "soon"
            return f"🔔 Reminder set: '{reminder_text}' at {time_display}"
            
        except Exception as e:
            return f"Error setting reminder: {str(e)}"
    
    async def _list_reminders(self) -> str:
        """List all reminders"""
        try:
            if not self.reminders:
                return "🔔 No reminders found"
            
            active_reminders = [r for r in self.reminders if not r['completed']]
            
            if not active_reminders:
                return "🔔 No active reminders"
            
            result = "🔔 Active Reminders:\n"
            for reminder in active_reminders:
                time_str = "soon"
                if reminder['time']:
                    try:
                        time_obj = datetime.datetime.fromisoformat(reminder['time'])
                        time_str = time_obj.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                result += f"• {reminder['text']} - {time_str}\n"
            
            return result
            
        except Exception as e:
            return f"Error listing reminders: {str(e)}"
    
    async def _delete_reminder(self, query: str) -> str:
        """Delete a reminder"""
        try:
            # Simple implementation - delete the most recent reminder
            if self.reminders:
                deleted = self.reminders.pop()
                self._save_json_file(self.reminders_file, self.reminders)
                return f"🗑️ Deleted reminder: '{deleted['text']}'"
            else:
                return "🔔 No reminders to delete"
                
        except Exception as e:
            return f"Error deleting reminder: {str(e)}"
    
    async def _handle_schedule(self, query: str) -> str:
        """Handle schedule operations"""
        try:
            if "add" in query.lower() or "schedule" in query.lower():
                return await self._add_appointment(query)
            elif "today" in query.lower():
                return await self._show_today_schedule()
            elif "week" in query.lower():
                return await self._show_week_schedule()
            else:
                return "📅 Schedule options: add appointment, show today, show week"
                
        except Exception as e:
            return f"Error handling schedule: {str(e)}"
    
    async def _add_appointment(self, query: str) -> str:
        """Add appointment to schedule"""
        try:
            # Extract appointment details
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the appointment details from this request:
                "{query}"
                
                Respond in format: "title:date:time" (e.g., "Doctor appointment:2024-01-15:14:00")
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                parts = response['response'].strip().split(':')
                if len(parts) >= 3:
                    title, date_str, time_str = parts[0], parts[1], parts[2]
                    
                    # Parse datetime
                    try:
                        appointment_time = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        date_key = date_str
                        
                        if date_key not in self.schedule:
                            self.schedule[date_key] = []
                        
                        self.schedule[date_key].append({
                            "title": title,
                            "time": time_str,
                            "created": datetime.datetime.now().isoformat()
                        })
                        
                        self._save_json_file(self.schedule_file, self.schedule)
                        return f"📅 Appointment added: '{title}' on {date_str} at {time_str}"
                    except:
                        return "Please specify a valid date and time."
                else:
                    return "Please specify appointment title, date, and time."
            else:
                return "Schedule management requires more specific input."
                
        except Exception as e:
            return f"Error adding appointment: {str(e)}"
    
    async def _show_today_schedule(self) -> str:
        """Show today's schedule"""
        try:
            today = datetime.date.today().isoformat()
            
            if today in self.schedule:
                appointments = self.schedule[today]
                result = f"📅 Today's Schedule ({today}):\n"
                for apt in sorted(appointments, key=lambda x: x['time']):
                    result += f"• {apt['time']} - {apt['title']}\n"
                return result
            else:
                return f"📅 No appointments scheduled for today ({today})"
                
        except Exception as e:
            return f"Error showing today's schedule: {str(e)}"
    
    async def _show_week_schedule(self) -> str:
        """Show this week's schedule"""
        try:
            today = datetime.date.today()
            week_start = today - datetime.timedelta(days=today.weekday())
            
            result = "📅 This Week's Schedule:\n"
            has_appointments = False
            
            for i in range(7):
                day = week_start + datetime.timedelta(days=i)
                day_str = day.isoformat()
                day_name = day.strftime("%A")
                
                if day_str in self.schedule:
                    appointments = self.schedule[day_str]
                    result += f"\n{day_name} ({day_str}):\n"
                    for apt in sorted(appointments, key=lambda x: x['time']):
                        result += f"  • {apt['time']} - {apt['title']}\n"
                    has_appointments = True
            
            if not has_appointments:
                result += "No appointments scheduled this week."
            
            return result
            
        except Exception as e:
            return f"Error showing week schedule: {str(e)}"
    
    async def _handle_info(self, query: str) -> str:
        """Handle information requests"""
        try:
            if "weather" in query.lower():
                return await self._get_weather()
            elif "time" in query.lower():
                return await self._get_time()
            elif "date" in query.lower():
                return await self._get_date()
            else:
                return await self._get_general_info(query)
                
        except Exception as e:
            return f"Error getting information: {str(e)}"
    
    async def _get_weather(self) -> str:
        """Get weather information"""
        try:
            # This is a placeholder - in production, you'd use a weather API
            return "🌤️ Weather: Partly cloudy, 22°C. (Weather API integration needed)"
            
        except Exception as e:
            return f"Error getting weather: {str(e)}"
    
    async def _get_time(self) -> str:
        """Get current time"""
        try:
            now = datetime.datetime.now()
            return f"🕐 Current time: {now.strftime('%H:%M:%S')}"
            
        except Exception as e:
            return f"Error getting time: {str(e)}"
    
    async def _get_date(self) -> str:
        """Get current date"""
        try:
            today = datetime.date.today()
            day_name = today.strftime("%A")
            return f"📅 Today is {day_name}, {today.strftime('%B %d, %Y')}"
            
        except Exception as e:
            return f"Error getting date: {str(e)}"
    
    async def _get_general_info(self, query: str) -> str:
        """Get general information"""
        if OLLAMA_AVAILABLE:
            try:
                info_prompt = f"""
                Provide a helpful, concise answer to this question:
                "{query}"
                
                Keep the response brief and informative.
                """
                response = ollama.generate(model=self.tiny_model, prompt=info_prompt)
                return f"ℹ️ {response['response']}"
            except Exception as e:
                logging.warning(f"Info LLM response failed: {e}")
        
        return "ℹ️ Information lookup requires LLM support or specific queries like weather, time, or date."
    
    async def _handle_task(self, query: str) -> str:
        """Handle task management"""
        try:
            if "add" in query.lower():
                return await self._add_task(query)
            elif "list" in query.lower():
                return await self._list_tasks()
            elif "complete" in query.lower() or "done" in query.lower():
                return await self._complete_task(query)
            else:
                return "✅ Task options: add task, list tasks, complete task"
                
        except Exception as e:
            return f"Error handling task: {str(e)}"
    
    async def _add_task(self, query: str) -> str:
        """Add a new task"""
        try:
            task_text = query.replace("add task", "").replace("add", "").strip()
            
            if not task_text:
                return "Please specify the task to add."
            
            task = {
                "id": len(self.tasks) + 1,
                "text": task_text,
                "created": datetime.datetime.now().isoformat(),
                "completed": False
            }
            
            self.tasks.append(task)
            self._save_json_file(self.tasks_file, self.tasks)
            
            return f"✅ Task added: '{task_text}'"
            
        except Exception as e:
            return f"Error adding task: {str(e)}"
    
    async def _list_tasks(self) -> str:
        """List all tasks"""
        try:
            if not self.tasks:
                return "✅ No tasks found"
            
            pending_tasks = [t for t in self.tasks if not t['completed']]
            
            if not pending_tasks:
                return "✅ No pending tasks"
            
            result = "✅ Pending Tasks:\n"
            for task in pending_tasks:
                result += f"• {task['text']}\n"
            
            return result
            
        except Exception as e:
            return f"Error listing tasks: {str(e)}"
    
    async def _complete_task(self, query: str) -> str:
        """Mark a task as complete"""
        try:
            # Simple implementation - complete the first pending task
            for task in self.tasks:
                if not task['completed']:
                    task['completed'] = True
                    task['completed_at'] = datetime.datetime.now().isoformat()
                    self._save_json_file(self.tasks_file, self.tasks)
                    return f"✅ Task completed: '{task['text']}'"
            
            return "✅ No pending tasks to complete"
            
        except Exception as e:
            return f"Error completing task: {str(e)}"
    
    async def _handle_time(self, query: str) -> str:
        """Handle time-related queries"""
        try:
            if "now" in query.lower() or "current" in query.lower():
                now = datetime.datetime.now()
                return f"🕐 Current time: {now.strftime('%H:%M:%S')}\n📅 Date: {now.strftime('%A, %B %d, %Y')}"
            elif "today" in query.lower():
                return await self._get_date()
            elif "tomorrow" in query.lower():
                tomorrow = datetime.date.today() + datetime.timedelta(days=1)
                return f"📅 Tomorrow is {tomorrow.strftime('%A, %B %d, %Y')}"
            else:
                return await self._get_time()
                
        except Exception as e:
            return f"Error handling time query: {str(e)}"
    
    async def _handle_search(self, query: str) -> str:
        """Handle search queries"""
        return "🔍 Search functionality coming soon. Currently supports reminders, schedule, and basic information."
    
    async def _handle_general(self, query: str) -> str:
        """Handle general personal assistant queries"""
        if OLLAMA_AVAILABLE:
            try:
                general_prompt = f"""
                You are a personal assistant. Help with this query:
                "{query}"
                
                Provide a helpful response about reminders, scheduling, tasks, or information.
                """
                response = ollama.generate(model=self.tiny_model, prompt=general_prompt)
                return response['response']
            except Exception as e:
                logging.warning(f"General LLM response failed: {e}")
        
        return "I can help with personal assistant tasks like setting reminders, managing your schedule, tracking tasks, and getting information. What would you like to do?"

# Compatibility alias
Agent = PersonalAssistantAgent 