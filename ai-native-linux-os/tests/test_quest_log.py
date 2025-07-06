#!/usr/bin/env python3
"""
Test suite for Quest Log system
"""

import unittest
import sys
import os
import tempfile
import sqlite3
import json
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quest_log.quest_log_daemon import QuestLogDaemon
from quest_log.quest_log_cli import QuestLogCLI


class TestQuestLogDaemon(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_quest_log.db')
        self.daemon = QuestLogDaemon(self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_database_setup(self):
        """Test database initialization"""
        self.assertTrue(os.path.exists(self.db_path))
        
        # Check if tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('events', tables)
        self.assertIn('commands', tables)
        
        conn.close()
    
    def test_log_event(self):
        """Test event logging"""
        self.daemon.log_event('test_event', 'test_source', {'key': 'value'}, {'meta': 'data'})
        
        # Verify event was logged
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE event_type = 'test_event'")
        event = cursor.fetchone()
        
        self.assertIsNotNone(event)
        self.assertEqual(event[2], 'test_event')  # event_type
        self.assertEqual(event[3], 'test_source')  # source
        
        conn.close()
    
    def test_log_command(self):
        """Test command logging"""
        self.daemon.log_command('test_user', 'ls -la', '/home/test', 0, 'output', 1.5)
        
        # Verify command was logged
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM commands WHERE command = 'ls -la'")
        command = cursor.fetchone()
        
        self.assertIsNotNone(command)
        self.assertEqual(command[2], 'test_user')  # user
        self.assertEqual(command[3], 'ls -la')  # command
        self.assertEqual(command[4], '/home/test')  # working_directory
        self.assertEqual(command[5], 0)  # exit_code
        
        conn.close()


class TestQuestLogCLI(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_quest_log.db')
        
        # Create test database with sample data
        daemon = QuestLogDaemon(self.db_path)
        daemon.log_event('test_event', 'test_source', {'key': 'value'})
        daemon.log_command('test_user', 'ls -la', '/home/test', 0, 'output', 1.5)
        
        self.cli = QuestLogCLI(self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_events(self):
        """Test getting events from database"""
        events = self.cli.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][2], 'test_event')  # event_type
        self.assertEqual(events[0][3], 'test_source')  # source
    
    def test_get_commands(self):
        """Test getting commands from database"""
        commands = self.cli.get_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][2], 'test_user')  # user
        self.assertEqual(commands[0][3], 'ls -la')  # command
    
    def test_get_stats(self):
        """Test getting statistics"""
        stats = self.cli.get_stats()
        self.assertEqual(stats['total_events'], 1)
        self.assertEqual(stats['total_commands'], 1)
        self.assertEqual(len(stats['event_types']), 1)
        self.assertEqual(stats['event_types'][0][0], 'test_event')
    
    def test_format_timestamp(self):
        """Test timestamp formatting"""
        timestamp = "2023-01-01 12:00:00"
        formatted = self.cli.format_timestamp(timestamp)
        self.assertEqual(formatted, "2023-01-01 12:00:00")
    
    def test_get_events_with_filters(self):
        """Test getting events with filters"""
        # Add more test data
        daemon = QuestLogDaemon(self.db_path)
        daemon.log_event('another_event', 'another_source', {'key': 'value'})
        
        # Test type filter
        events = self.cli.get_events(event_type='test_event')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][2], 'test_event')
        
        # Test source filter
        events = self.cli.get_events(source='test_source')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][3], 'test_source')
        
        # Test limit
        events = self.cli.get_events(limit=1)
        self.assertEqual(len(events), 1)


if __name__ == '__main__':
    unittest.main()