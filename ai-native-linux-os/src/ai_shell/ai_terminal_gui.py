#!/usr/bin/env python3
"""
AI Terminal GUI - A conversational interface for the AI-Native Linux OS
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import time
import json
import asyncio
from pathlib import Path
import subprocess
import sys
import os

# Import the AI orchestrator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from ai_orchestrator.main_ai_controller import MainAIController
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    # Fallback to original AI shell for compatibility
    from ai_shell import AIShellAssistant
    ORCHESTRATOR_AVAILABLE = False


class AITerminalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 AI-Native Linux OS - Multi-Agent Interface")
        self.root.geometry("900x700")
        self.root.configure(bg='#2c3e50')
        
        # Initialize AI system
        self.init_ai_system()
        
        # Queue for thread communication
        self.message_queue = queue.Queue()
        
        # Setup GUI
        self.setup_gui()
        
        # Start message processing
        self.process_messages()
        
        # Show welcome and status
        self.show_welcome_message()
        
        # Setup auto-refresh for agent status
        self.setup_status_refresh()
        
    def init_ai_system(self):
        """Initialize the AI system (orchestrator or fallback)"""
        if ORCHESTRATOR_AVAILABLE:
            try:
                self.ai_controller = MainAIController()
                self.ai_mode = "orchestrator"
                self.agent_status = {}
            except Exception as e:
                print(f"Failed to initialize AI orchestrator: {e}")
                self.ai_controller = AIShellAssistant()
                self.ai_mode = "fallback"
        else:
            self.ai_controller = AIShellAssistant()
            self.ai_mode = "fallback"
            if hasattr(self.ai_controller, 'load_conversation'):
                self.ai_controller.load_conversation()
    
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header with title and status
        self.setup_header(main_frame)
        
        # Agent status panel (only for orchestrator mode)
        if self.ai_mode == "orchestrator":
            self.setup_agent_status_panel(main_frame)
        
        # Chat area
        self.setup_chat_area(main_frame)
        
        # Input area
        self.setup_input_area(main_frame)
        
        # Control buttons
        self.setup_control_buttons(main_frame)
    
    def setup_header(self, parent):
        """Setup the header with title and mode indicator"""
        header_frame = tk.Frame(parent, bg='#2c3e50')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title
        title_label = tk.Label(
            header_frame, 
            text="🤖 AI-Native Linux OS",
            font=('Ubuntu', 16, 'bold'),
            bg='#2c3e50', 
            fg='#ecf0f1'
        )
        title_label.pack(side=tk.LEFT)
        
        # Mode indicator
        mode_text = "Multi-Agent Mode" if self.ai_mode == "orchestrator" else "Compatibility Mode"
        mode_color = "#27ae60" if self.ai_mode == "orchestrator" else "#f39c12"
        
        self.mode_label = tk.Label(
            header_frame,
            text=f"• {mode_text}",
            font=('Ubuntu', 10),
            bg='#2c3e50',
            fg=mode_color
        )
        self.mode_label.pack(side=tk.RIGHT)
    
    def setup_agent_status_panel(self, parent):
        """Setup agent status panel for orchestrator mode"""
        status_frame = tk.LabelFrame(
            parent,
            text="Agent Status",
            font=('Ubuntu', 10, 'bold'),
            bg='#34495e',
            fg='#ecf0f1',
            relief=tk.RAISED,
            bd=2
        )
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create status indicators for each agent
        self.agent_indicators = {}
        agents = [
            ("system_agent", "System Monitor", "🔍"),
            ("file_management_agent", "File Manager", "📁"),
            ("software_install_agent", "Software Installer", "📦"),
            ("shell_assistant_agent", "Shell Assistant", "💻"),
            ("activity_tracker_agent", "Activity Tracker", "📊")
        ]
        
        indicators_frame = tk.Frame(status_frame, bg='#34495e')
        indicators_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for i, (agent_id, agent_name, icon) in enumerate(agents):
            agent_frame = tk.Frame(indicators_frame, bg='#34495e')
            agent_frame.grid(row=0, column=i, padx=5, sticky='ew')
            
            # Agent icon and name
            tk.Label(
                agent_frame,
                text=f"{icon} {agent_name}",
                font=('Ubuntu', 8),
                bg='#34495e',
                fg='#ecf0f1'
            ).pack()
            
            # Status indicator
            status_indicator = tk.Label(
                agent_frame,
                text="●",
                font=('Ubuntu', 12),
                bg='#34495e',
                fg='#95a5a6'  # Default gray
            )
            status_indicator.pack()
            
            self.agent_indicators[agent_id] = status_indicator
        
        # Configure grid weights
        for i in range(len(agents)):
            indicators_frame.grid_columnconfigure(i, weight=1)
    
    def setup_chat_area(self, parent):
        """Setup the main chat conversation area"""
        chat_frame = tk.Frame(parent, bg='#2c3e50')
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Chat display with scrollbar
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=('Ubuntu Mono', 11),
            bg='#34495e',
            fg='#ecf0f1',
            insertbackground='#ecf0f1',
            selectbackground='#3498db',
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for different message types
        self.chat_display.tag_configure("user", foreground="#3498db", font=('Ubuntu Mono', 11, 'bold'))
        self.chat_display.tag_configure("ai", foreground="#2ecc71", font=('Ubuntu Mono', 11, 'bold'))
        self.chat_display.tag_configure("system", foreground="#f39c12", font=('Ubuntu Mono', 10))
        self.chat_display.tag_configure("command", foreground="#e74c3c", font=('Ubuntu Mono', 10, 'bold'))
        self.chat_display.tag_configure("success", foreground="#27ae60")
        self.chat_display.tag_configure("warning", foreground="#f39c12")
        self.chat_display.tag_configure("error", foreground="#e74c3c")
        self.chat_display.tag_configure("agent", foreground="#9b59b6", font=('Ubuntu Mono', 10, 'italic'))
    
    def setup_input_area(self, parent):
        """Setup the user input area"""
        input_frame = tk.Frame(parent, bg='#2c3e50')
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Input label
        tk.Label(
            input_frame,
            text="💬 Talk to your AI assistants:",
            font=('Ubuntu', 10, 'bold'),
            bg='#2c3e50',
            fg='#ecf0f1'
        ).pack(anchor='w', pady=(0, 5))
        
        # Input entry with send button
        entry_frame = tk.Frame(input_frame, bg='#2c3e50')
        entry_frame.pack(fill=tk.X)
        
        self.user_input = tk.Entry(
            entry_frame,
            font=('Ubuntu', 12),
            bg='#ecf0f1',
            fg='#2c3e50',
            relief=tk.FLAT,
            bd=0
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.user_input.bind('<Return>', self.handle_user_input)
        self.user_input.focus()
        
        # Send button
        self.send_button = tk.Button(
            entry_frame,
            text="Send",
            font=('Ubuntu', 10, 'bold'),
            bg='#3498db',
            fg='white',
            relief=tk.FLAT,
            bd=0,
            padx=20,
            command=self.handle_user_input
        )
        self.send_button.pack(side=tk.RIGHT)
    
    def setup_control_buttons(self, parent):
        """Setup control buttons"""
        control_frame = tk.Frame(parent, bg='#2c3e50')
        control_frame.pack(fill=tk.X)
        
        # Emergency stop button (only for orchestrator mode)
        if self.ai_mode == "orchestrator":
            self.emergency_button = tk.Button(
                control_frame,
                text="🛑 Emergency Stop",
                font=('Ubuntu', 10, 'bold'),
                bg='#e74c3c',
                fg='white',
                relief=tk.FLAT,
                bd=0,
                padx=15,
                command=self.emergency_stop
            )
            self.emergency_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear chat button
        clear_button = tk.Button(
            control_frame,
            text="🗑️ Clear Chat",
            font=('Ubuntu', 10),
            bg='#95a5a6',
            fg='white',
            relief=tk.FLAT,
            bd=0,
            padx=15,
            command=self.clear_chat
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Agent status button (only for orchestrator mode)
        if self.ai_mode == "orchestrator":
            status_button = tk.Button(
                control_frame,
                text="📊 Agent Status",
                font=('Ubuntu', 10),
                bg='#9b59b6',
                fg='white',
                relief=tk.FLAT,
                bd=0,
                padx=15,
                command=self.show_agent_details
            )
            status_button.pack(side=tk.LEFT)
    
    def show_welcome_message(self):
        """Show welcome message based on mode"""
        if self.ai_mode == "orchestrator":
            self.add_system_message("🚀 Welcome to AI-Native Linux OS!")
            self.add_system_message("Multi-Agent System Active:")
            self.add_system_message("• 🔍 System Agent - Hardware monitoring & diagnostics")
            self.add_system_message("• 📁 File Manager - Smart file organization")
            self.add_system_message("• 📦 Software Installer - Complex software installations")
            self.add_system_message("• 💻 Shell Assistant - Natural language commands")
            self.add_system_message("• 📊 Activity Tracker - Usage patterns & insights")
            self.add_system_message("")
            self.add_system_message("Try saying:")
            self.add_system_message("• 'Check system health'")
            self.add_system_message("• 'Organize my downloads folder'")
            self.add_system_message("• 'Install Docker'")
            self.add_system_message("• 'Show me my activity patterns'")
        else:
            self.add_system_message("👋 Hi! I'm your AI assistant (Compatibility Mode)")
            self.add_system_message("Try saying things like:")
            self.add_system_message("• 'Show me my files'")
            self.add_system_message("• 'What's taking up disk space?'")
            self.add_system_message("• 'Create a folder called Photos'")
            self.add_system_message("• 'Help me learn AI'")
    
    def setup_status_refresh(self):
        """Setup automatic status refresh for agent indicators"""
        if self.ai_mode == "orchestrator":
            self.refresh_agent_status()
            # Schedule next refresh
            self.root.after(5000, self.setup_status_refresh)  # Refresh every 5 seconds
    
    def refresh_agent_status(self):
        """Refresh agent status indicators"""
        if self.ai_mode != "orchestrator":
            return
        
        def update_status():
            try:
                # Get agent status asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                status = loop.run_until_complete(self.ai_controller.get_system_status())
                
                # Update indicators on main thread
                self.root.after(0, lambda: self.update_status_indicators(status))
                
            except Exception as e:
                print(f"Failed to refresh agent status: {e}")
        
        # Run status update in background thread
        threading.Thread(target=update_status, daemon=True).start()
    
    def update_status_indicators(self, status):
        """Update agent status indicators in the GUI"""
        if 'agents' not in status:
            return
        
        agent_status = status['agents']
        
        for agent_id, indicator in self.agent_indicators.items():
            if agent_id in agent_status:
                agent_info = agent_status[agent_id]
                state = agent_info.get('state', 'unknown')
                
                # Set color based on state
                if state == 'idle':
                    color = '#27ae60'  # Green
                elif state == 'processing':
                    color = '#f39c12'  # Orange
                elif state == 'error':
                    color = '#e74c3c'  # Red
                else:
                    color = '#95a5a6'  # Gray
                
                indicator.config(fg=color)
    
    def handle_user_input(self, event=None):
        """Handle user input and send to AI system"""
        user_text = self.user_input.get().strip()
        if not user_text:
            return
        
        # Clear input
        self.user_input.delete(0, tk.END)
        
        # Add user message to chat
        self.add_user_message(user_text)
        
        # Process in background thread
        def process_input():
            try:
                if self.ai_mode == "orchestrator":
                    # Use new orchestrator
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    response = loop.run_until_complete(
                        self.ai_controller.process_user_request(user_text)
                    )
                    
                    self.message_queue.put(('ai_response', response))
                else:
                    # Use fallback assistant
                    response = self.ai_controller.process_input(user_text)
                    self.message_queue.put(('ai_response', response))
                    
            except Exception as e:
                self.message_queue.put(('error', f"Error processing request: {e}"))
        
        # Start processing thread
        threading.Thread(target=process_input, daemon=True).start()
        
        # Show processing indicator
        self.add_system_message("🤔 Processing your request...")
    
    def process_messages(self):
        """Process messages from background threads"""
        try:
            while True:
                msg_type, content = self.message_queue.get_nowait()
                
                if msg_type == 'ai_response':
                    self.handle_ai_response(content)
                elif msg_type == 'error':
                    self.add_error_message(content)
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_messages)
    
    def handle_ai_response(self, response):
        """Handle AI response and display appropriately"""
        if self.ai_mode == "orchestrator":
            # Handle orchestrator response
            if isinstance(response, dict):
                if 'coordinated_response' in response:
                    self.add_ai_message(response['coordinated_response'])
                
                if 'agent_responses' in response:
                    for agent_id, agent_response in response['agent_responses'].items():
                        if agent_response and 'status' in agent_response:
                            self.add_agent_message(agent_id, agent_response)
                
                if 'command' in response:
                    self.add_command_message(response['command'])
                    if 'output' in response:
                        self.add_command_output(response['output'])
            else:
                self.add_ai_message(str(response))
        else:
            # Handle fallback assistant response
            if isinstance(response, dict):
                if 'command' in response:
                    self.add_command_message(response['command'])
                if 'explanation' in response:
                    self.add_ai_message(response['explanation'])
                if 'output' in response:
                    self.add_command_output(response['output'])
            else:
                self.add_ai_message(str(response))
    
    def add_user_message(self, message):
        """Add user message to chat"""
        self.chat_display.insert(tk.END, f"You: {message}\n", "user")
        self.chat_display.see(tk.END)
    
    def add_ai_message(self, message):
        """Add AI response to chat"""
        self.chat_display.insert(tk.END, f"🤖 AI: {message}\n", "ai")
        self.chat_display.see(tk.END)
    
    def add_agent_message(self, agent_id, response):
        """Add agent-specific message to chat"""
        agent_names = {
            'system_agent': '🔍 System',
            'file_management_agent': '📁 File Manager',
            'software_install_agent': '📦 Installer',
            'shell_assistant_agent': '💻 Shell',
            'activity_tracker_agent': '📊 Tracker'
        }
        
        agent_name = agent_names.get(agent_id, agent_id)
        
        if isinstance(response, dict) and 'message' in response:
            message = response['message']
        else:
            message = str(response)
        
        self.chat_display.insert(tk.END, f"{agent_name}: {message}\n", "agent")
        self.chat_display.see(tk.END)
    
    def add_system_message(self, message):
        """Add system message to chat"""
        self.chat_display.insert(tk.END, f"ℹ️  {message}\n", "system")
        self.chat_display.see(tk.END)
    
    def add_command_message(self, command):
        """Add command to chat"""
        self.chat_display.insert(tk.END, f"💻 Command: {command}\n", "command")
        self.chat_display.see(tk.END)
    
    def add_command_output(self, output):
        """Add command output to chat"""
        if output.strip():
            self.chat_display.insert(tk.END, f"Output: {output}\n", "success")
            self.chat_display.see(tk.END)
    
    def add_error_message(self, message):
        """Add error message to chat"""
        self.chat_display.insert(tk.END, f"❌ Error: {message}\n", "error")
        self.chat_display.see(tk.END)
    
    def emergency_stop(self):
        """Emergency stop all AI agents"""
        if self.ai_mode != "orchestrator":
            return
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            loop.run_until_complete(self.ai_controller.emergency_stop())
            
            self.add_system_message("🛑 Emergency stop activated - All agents stopped")
            
            # Update button state
            self.emergency_button.config(
                text="🟢 Restart Agents",
                bg='#27ae60',
                command=self.restart_agents
            )
            
        except Exception as e:
            self.add_error_message(f"Failed to execute emergency stop: {e}")
    
    def restart_agents(self):
        """Restart all AI agents"""
        if self.ai_mode != "orchestrator":
            return
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            loop.run_until_complete(self.ai_controller.start_all_agents())
            
            self.add_system_message("🟢 All agents restarted")
            
            # Update button state
            self.emergency_button.config(
                text="🛑 Emergency Stop",
                bg='#e74c3c',
                command=self.emergency_stop
            )
            
        except Exception as e:
            self.add_error_message(f"Failed to restart agents: {e}")
    
    def clear_chat(self):
        """Clear the chat display"""
        self.chat_display.delete(1.0, tk.END)
        self.show_welcome_message()
    
    def show_agent_details(self):
        """Show detailed agent status in a popup"""
        if self.ai_mode != "orchestrator":
            return
        
        def get_details():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                status = loop.run_until_complete(self.ai_controller.get_system_status())
                
                # Create popup window
                self.root.after(0, lambda: self.create_status_popup(status))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to get agent status: {e}"))
        
        threading.Thread(target=get_details, daemon=True).start()
    
    def create_status_popup(self, status):
        """Create agent status popup window"""
        popup = tk.Toplevel(self.root)
        popup.title("Agent Status Details")
        popup.geometry("600x400")
        popup.configure(bg='#2c3e50')
        
        # Status text area
        status_text = scrolledtext.ScrolledText(
            popup,
            wrap=tk.WORD,
            font=('Ubuntu Mono', 10),
            bg='#34495e',
            fg='#ecf0f1'
        )
        status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format and display status
        status_text.insert(tk.END, json.dumps(status, indent=2))
        status_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = AITerminalGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 