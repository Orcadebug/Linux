#!/usr/bin/env python3
"""
AI Shell Daemon - System-level AI assistant service
Runs as a SystemD service for deep OS integration
"""

import sys
import os
import socket
import json
import logging
import threading
import time
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/opt/ai-native-linux/src')

from ai_shell.ai_shell import AIShellAssistant

class AIShellDaemon:
    def __init__(self, socket_path='/tmp/ai-shell.sock', log_file='/var/log/ai-native-linux/ai-shell.log'):
        self.socket_path = socket_path
        self.log_file = log_file
        self.running = False
        self.socket_server = None
        self.ai_assistant = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AIShellDaemon')
        
        # Initialize AI assistant
        self.ai_assistant = AIShellAssistant()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
    
    def start(self):
        """Start the daemon service"""
        self.logger.info("Starting AI Shell Daemon...")
        
        # Remove existing socket if it exists
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        # Create Unix socket
        self.socket_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_server.bind(self.socket_path)
        self.socket_server.listen(10)
        
        # Set socket permissions
        os.chmod(self.socket_path, 0o666)
        
        self.running = True
        self.logger.info(f"AI Shell Daemon listening on {self.socket_path}")
        
        # Main service loop
        while self.running:
            try:
                client_socket, addr = self.socket_server.accept()
                # Handle client in separate thread
                thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                thread.daemon = True
                thread.start()
            except socket.error as e:
                if self.running:
                    self.logger.error(f"Socket error: {e}")
                break
    
    def handle_client(self, client_socket):
        """Handle individual client connections"""
        try:
            # Receive data
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return
            
            # Parse JSON request
            try:
                request = json.loads(data)
                command = request.get('command', '')
                context = request.get('context', {})
            except json.JSONDecodeError:
                # Fallback to treating as plain text command
                command = data.strip()
                context = {}
            
            self.logger.info(f"Processing command: {command}")
            
            # Process command through AI assistant
            try:
                result = self.ai_assistant.process_command(command, context)
                
                # Format response
                response = {
                    'success': True,
                    'result': result,
                    'timestamp': time.time()
                }
            except Exception as e:
                self.logger.error(f"Error processing command: {e}")
                response = {
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time()
                }
            
            # Send response
            response_data = json.dumps(response).encode('utf-8')
            client_socket.sendall(response_data)
            
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()
    
    def shutdown(self, signum=None, frame=None):
        """Shutdown the daemon gracefully"""
        self.logger.info("Shutting down AI Shell Daemon...")
        self.running = False
        
        if self.socket_server:
            self.socket_server.close()
        
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        self.logger.info("AI Shell Daemon stopped")
        sys.exit(0)

def main():
    """Main entry point for daemon"""
    # Ensure log directory exists
    log_dir = Path('/var/log/ai-native-linux')
    log_dir.mkdir(exist_ok=True)
    
    # Create and start daemon
    daemon = AIShellDaemon()
    daemon.start()

if __name__ == '__main__':
    main() 