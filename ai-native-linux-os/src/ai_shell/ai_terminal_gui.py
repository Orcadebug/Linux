#!/usr/bin/env python3
"""
AI Terminal GUI - ChatGPT-like interface for the AI-Native Linux OS
Integrates with the specialized mixture of agents architecture
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
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
    ORCHESTRATOR_AVAILABLE = False
    print("Warning: AI Orchestrator not available")

class AITerminalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 AI-Native Linux OS Hub - Mixture of Agents")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2c3e50')
        
        # Initialize AI system
        self.init_ai_system()
        
        # Queue for thread communication
        self.message_queue = queue.Queue()
        
        # Setup GUI
        self.setup_gui()
        
        # Start message processing
        self.process_messages()
        
        # Show welcome message
        self.show_welcome_message()
        
        # Agent status tracking
        self.agent_status_update_interval = 5000  # 5 seconds
        self.update_agent_status()
        
    def init_ai_system(self):
        """Initialize the AI system"""
        if ORCHESTRATOR_AVAILABLE:
            self.ai_controller = MainAIController()
            self.ai_available = True
        else:
            self.ai_controller = None
            self.ai_available = False
    
    def setup_gui(self):
        """Setup the ChatGPT-like GUI"""
        # Create main frame
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🤖 AI-Native Linux OS Hub",
            font=('Arial', 16, 'bold'),
            bg='#2c3e50',
            fg='#ecf0f1'
        )
        title_label.pack(pady=(0, 10))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Chat tab
        self.setup_chat_tab()
        
        # Agent status tab
        self.setup_agent_status_tab()
        
        # Settings tab
        self.setup_settings_tab()
    
    def setup_chat_tab(self):
        """Setup the main chat interface tab"""
        chat_frame = tk.Frame(self.notebook, bg='#34495e')
        self.notebook.add(chat_frame, text='💬 Chat')
        
        # Chat display area
        chat_display_frame = tk.Frame(chat_frame, bg='#34495e')
        chat_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chat history display (ChatGPT-like)
        self.chat_display = scrolledtext.ScrolledText(
            chat_display_frame,
            wrap=tk.WORD,
            state='disabled',
            bg='#2c3e50',
            fg='#ecf0f1',
            font=('Consolas', 11),
            insertbackground='#ecf0f1',
            selectbackground='#3498db',
            selectforeground='#ecf0f1'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Input area
        input_frame = tk.Frame(chat_frame, bg='#34495e')
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Input box
        self.input_entry = tk.Entry(
            input_frame,
            font=('Consolas', 11),
            bg='#ecf0f1',
            fg='#2c3e50',
            insertbackground='#2c3e50'
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", self.send_query)
        self.input_entry.bind("<Up>", self.history_up)
        self.input_entry.bind("<Down>", self.history_down)
        
        # Send button
        self.send_button = tk.Button(
            input_frame,
            text="Send",
            command=self.send_query,
            bg='#3498db',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            padx=20
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # Quick action buttons
        quick_actions_frame = tk.Frame(chat_frame, bg='#34495e')
        quick_actions_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        quick_actions = [
            ("📊 System Info", "show system information"),
            ("📁 Organize Files", "organize my files"),
            ("🔄 Update System", "update the system"),
            ("🎵 Play Music", "play music"),
            ("📧 Check Email", "check my email"),
            ("⏰ Set Reminder", "set a reminder"),
            ("🔍 Troubleshoot", "diagnose system issues"),
            ("🧹 Cleanup", "cleanup duplicate files")
        ]
        
        for i, (text, command) in enumerate(quick_actions):
            btn = tk.Button(
                quick_actions_frame,
                text=text,
                command=lambda cmd=command: self.quick_action(cmd),
                bg='#95a5a6',
                fg='#2c3e50',
                font=('Arial', 9),
                relief=tk.FLAT,
                padx=10,
                pady=5
            )
            btn.grid(row=i//4, column=i%4, padx=5, pady=5, sticky='ew')
        
        # Configure grid weights
        for i in range(4):
            quick_actions_frame.grid_columnconfigure(i, weight=1)
        
        # Status bar
        self.status_bar = tk.Label(
            chat_frame,
            text="Ready",
            bg='#2c3e50',
            fg='#ecf0f1',
            font=('Arial', 9),
            anchor='w'
        )
        self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Command history
        self.command_history = []
        self.history_index = -1
    
    def setup_agent_status_tab(self):
        """Setup the agent status monitoring tab"""
        status_frame = tk.Frame(self.notebook, bg='#34495e')
        self.notebook.add(status_frame, text='🤖 Agents')
        
        # Agent status display
        self.agent_status_text = scrolledtext.ScrolledText(
            status_frame,
            wrap=tk.WORD,
            state='disabled',
            bg='#2c3e50',
            fg='#ecf0f1',
            font=('Consolas', 10)
        )
        self.agent_status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Agent control buttons
        control_frame = tk.Frame(status_frame, bg='#34495e')
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Button(
            control_frame,
            text="Refresh Status",
            command=self.refresh_agent_status,
            bg='#3498db',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            padx=15
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            control_frame,
            text="Unload All Agents",
            command=self.unload_all_agents,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            padx=15
        ).pack(side=tk.LEFT, padx=5)
    
    def setup_settings_tab(self):
        """Setup the settings tab"""
        settings_frame = tk.Frame(self.notebook, bg='#34495e')
        self.notebook.add(settings_frame, text='⚙️ Settings')
        
        # Settings content
        settings_label = tk.Label(
            settings_frame,
            text="AI-Native Linux OS Settings",
            font=('Arial', 14, 'bold'),
            bg='#34495e',
            fg='#ecf0f1'
        )
        settings_label.pack(pady=20)
        
        # Model selection
        model_frame = tk.Frame(settings_frame, bg='#34495e')
        model_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            model_frame,
            text="Central LLM Model:",
            bg='#34495e',
            fg='#ecf0f1',
            font=('Arial', 11)
        ).pack(side=tk.LEFT)
        
        self.model_var = tk.StringVar(value="phi3:mini")
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=["phi3:mini", "phi3", "tinyllm", "mistral"],
            state="readonly"
        )
        model_combo.pack(side=tk.RIGHT, padx=10)
        
        # Auto-unload settings
        auto_unload_frame = tk.Frame(settings_frame, bg='#34495e')
        auto_unload_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.auto_unload_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            auto_unload_frame,
            text="Auto-unload dormant agents after 5 minutes",
            variable=self.auto_unload_var,
            bg='#34495e',
            fg='#ecf0f1',
            font=('Arial', 11),
            selectcolor='#2c3e50'
        ).pack(side=tk.LEFT)
    
    def show_welcome_message(self):
        """Show welcome message"""
        if self.ai_available:
            welcome = self.ai_controller.get_welcome_message()
        else:
            welcome = "⚠️ AI Controller not available. Please check installation."
        
        self.append_to_chat("AI", welcome, "#3498db")
    
    def append_to_chat(self, sender, message, color="#ecf0f1"):
        """Append message to chat display"""
        self.chat_display.configure(state='normal')
        
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S")
        
        # Add sender and message
        self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: ", "sender")
        self.chat_display.insert(tk.END, f"{message}\n\n", "message")
        
        # Configure tags for styling
        self.chat_display.tag_configure("sender", foreground=color, font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure("message", foreground="#ecf0f1", font=('Consolas', 10))
        
        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)
    
    def send_query(self, event=None):
        """Send user query to AI"""
        query = self.input_entry.get().strip()
        if not query:
            return
        
        # Add to history
        self.command_history.append(query)
        self.history_index = len(self.command_history)
        
        # Clear input
        self.input_entry.delete(0, tk.END)
        
        # Show user message
        self.append_to_chat("You", query, "#2ecc71")
        
        # Update status
        self.status_bar.config(text="Processing...")
        self.send_button.config(state='disabled')
        
        # Process query in background thread
        threading.Thread(target=self.process_query_async, args=(query,), daemon=True).start()
    
    def process_query_async(self, query):
        """Process query asynchronously"""
        try:
            if self.ai_available:
                # Run the async method in a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(self.ai_controller.classify_and_route(query))
                finally:
                    loop.close()
            else:
                response = "❌ AI Controller not available. Please check installation."
            
            # Send response back to main thread
            self.message_queue.put(('response', response))
            
        except Exception as e:
            self.message_queue.put(('error', str(e)))
    
    def quick_action(self, command):
        """Execute quick action"""
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, command)
        self.send_query()
    
    def history_up(self, event):
        """Navigate up in command history"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, self.command_history[self.history_index])
    
    def history_down(self, event):
        """Navigate down in command history"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, self.command_history[self.history_index])
        elif self.history_index >= len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.input_entry.delete(0, tk.END)
    
    def process_messages(self):
        """Process messages from background threads"""
        try:
            while True:
                message_type, data = self.message_queue.get_nowait()
                
                if message_type == 'response':
                    self.append_to_chat("AI", data, "#3498db")
                    self.status_bar.config(text="Ready")
                    self.send_button.config(state='normal')
                    
                elif message_type == 'error':
                    self.append_to_chat("AI", f"❌ Error: {data}", "#e74c3c")
                    self.status_bar.config(text="Error")
                    self.send_button.config(state='normal')
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_messages)
    
    def update_agent_status(self):
        """Update agent status display"""
        if self.ai_available:
            try:
                status = self.ai_controller.get_agent_status()
                
                status_text = "🤖 Agent Status Report\n"
                status_text += "=" * 50 + "\n\n"
                
                status_text += f"📊 Summary:\n"
                status_text += f"• Total Agents: {status['total_agents']}\n"
                status_text += f"• Memory Usage: {status['memory_usage']}\n\n"
                
                status_text += f"✅ Loaded Agents ({len(status['loaded_agents'])}):\n"
                if status['loaded_agents']:
                    for agent in status['loaded_agents']:
                        status_text += f"  • {agent.replace('_', ' ').title()}\n"
                else:
                    status_text += "  • None\n"
                
                status_text += f"\n💤 Dormant Agents ({len(status['dormant_agents'])}):\n"
                if status['dormant_agents']:
                    for agent in status['dormant_agents']:
                        status_text += f"  • {agent.replace('_', ' ').title()}\n"
                else:
                    status_text += "  • None\n"
                
                status_text += f"\n🔧 Agent Capabilities:\n"
                status_text += f"• System Management: Install/update software, manage services\n"
                status_text += f"• File & Storage: Organize files, cleanup, storage analysis\n"
                status_text += f"• Media: Playback control, library management\n"
                status_text += f"• Communication: Email, messages, notifications\n"
                status_text += f"• Personal Assistant: Reminders, scheduling, tasks\n"
                status_text += f"• Troubleshooting: Diagnose and fix issues\n"
                status_text += f"• Shell: Command execution, process management\n"
                status_text += f"• Activity: Usage tracking, pattern analysis\n"
                
                # Update display
                self.agent_status_text.configure(state='normal')
                self.agent_status_text.delete(1.0, tk.END)
                self.agent_status_text.insert(1.0, status_text)
                self.agent_status_text.configure(state='disabled')
                
            except Exception as e:
                self.agent_status_text.configure(state='normal')
                self.agent_status_text.delete(1.0, tk.END)
                self.agent_status_text.insert(1.0, f"Error getting agent status: {e}")
                self.agent_status_text.configure(state='disabled')
        
        # Schedule next update
        self.root.after(self.agent_status_update_interval, self.update_agent_status)
    
    def refresh_agent_status(self):
        """Manually refresh agent status"""
        self.update_agent_status()
    
    def unload_all_agents(self):
        """Unload all agents to free memory"""
        if self.ai_available:
            try:
                asyncio.run(self.ai_controller.unload_all_agents())
                self.append_to_chat("System", "All agents unloaded (returned to dormant state)", "#f39c12")
                self.update_agent_status()
            except Exception as e:
                self.append_to_chat("System", f"Error unloading agents: {e}", "#e74c3c")
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

def main():
    """Main entry point"""
    root = tk.Tk()
    app = AITerminalGUI(root)
    app.run()

if __name__ == "__main__":
    main() 