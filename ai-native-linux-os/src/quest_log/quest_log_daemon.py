#!/usr/bin/env python3
"""
Quest Log Daemon - System event and command logging service
"""

import os
import sys
import json
import time
import sqlite3
import threading
import signal
import logging
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class QuestLogDaemon:
    def __init__(self, db_path=None):
        self.db_path = db_path or Path.home() / ".quest_log.db"
        self.running = False
        self.setup_logging()
        self.setup_database()
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/quest_log.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QuestLogDaemon')
    
    def setup_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                data TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user TEXT NOT NULL,
                command TEXT NOT NULL,
                working_directory TEXT,
                exit_code INTEGER,
                output TEXT,
                duration REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def log_event(self, event_type, source, data=None, metadata=None):
        """Log a system event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (event_type, source, data, metadata)
            VALUES (?, ?, ?, ?)
        ''', (event_type, source, json.dumps(data), json.dumps(metadata)))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Event logged: {event_type} from {source}")
    
    def log_command(self, user, command, working_directory=None, exit_code=None, output=None, duration=None):
        """Log a shell command"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO commands (user, command, working_directory, exit_code, output, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user, command, working_directory, exit_code, output, duration))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Command logged: {command} by {user}")
    
    def monitor_bash_history(self):
        """Monitor bash history for new commands"""
        history_file = Path.home() / ".bash_history"
        last_position = 0
        
        if history_file.exists():
            last_position = history_file.stat().st_size
        
        while self.running:
            try:
                if history_file.exists():
                    current_size = history_file.stat().st_size
                    if current_size > last_position:
                        with open(history_file, 'r') as f:
                            f.seek(last_position)
                            new_commands = f.read().strip().split('\n')
                            
                            for command in new_commands:
                                if command.strip():
                                    self.log_command(
                                        user=os.getenv("USER", "unknown"),
                                        command=command.strip(),
                                        working_directory=os.getcwd()
                                    )
                            
                            last_position = current_size
                
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error monitoring bash history: {e}")
                time.sleep(5)
    
    def monitor_system_events(self):
        """Monitor various system events"""
        while self.running:
            try:
                # Monitor system load
                load_avg = os.getloadavg()
                if load_avg[0] > 2.0:  # High load threshold
                    self.log_event(
                        event_type="high_load",
                        source="system",
                        data={"load_avg": load_avg}
                    )
                
                # Monitor disk space
                disk_usage = os.statvfs('/')
                free_percent = (disk_usage.f_bavail * 100) / disk_usage.f_blocks
                if free_percent < 10:  # Low disk space threshold
                    self.log_event(
                        event_type="low_disk_space",
                        source="system",
                        data={"free_percent": free_percent}
                    )
                
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error monitoring system events: {e}")
                time.sleep(60)
    
    def start(self):
        """Start the daemon"""
        self.logger.info("Starting Quest Log Daemon...")
        self.running = True
        
        # Start monitoring threads
        bash_thread = threading.Thread(target=self.monitor_bash_history)
        system_thread = threading.Thread(target=self.monitor_system_events)
        
        bash_thread.daemon = True
        system_thread.daemon = True
        
        bash_thread.start()
        system_thread.start()
        
        # Main daemon loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Daemon interrupted by user")
        
        self.logger.info("Quest Log Daemon stopped")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--daemon":
            # Run as daemon
            daemon = QuestLogDaemon()
            daemon.start()
        else:
            print("Usage: quest_log_daemon.py [--daemon]")
    else:
        # Run in foreground
        daemon = QuestLogDaemon()
        daemon.start()


if __name__ == '__main__':
    main()