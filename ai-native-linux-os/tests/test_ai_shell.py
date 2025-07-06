#!/usr/bin/env python3
"""
Test suite for AI Shell Assistant
"""

import unittest
import sys
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_shell.ai_shell import AIShellAssistant


class TestAIShellAssistant(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.assistant = AIShellAssistant()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_defaults(self):
        """Test loading default configuration"""
        config = self.assistant.load_config(None)
        self.assertIn('llm_provider', config)
        self.assertIn('max_history', config)
        self.assertIn('safety_check', config)
        self.assertEqual(config['llm_provider'], 'local')
    
    def test_load_config_custom(self):
        """Test loading custom configuration"""
        config_file = os.path.join(self.temp_dir, 'config.json')
        custom_config = {
            'max_history': 100,
            'safety_check': False
        }
        
        with open(config_file, 'w') as f:
            json.dump(custom_config, f)
        
        config = self.assistant.load_config(config_file)
        self.assertEqual(config['max_history'], 100)
        self.assertEqual(config['safety_check'], False)
    
    def test_dangerous_command_detection(self):
        """Test dangerous command detection"""
        self.assertTrue(self.assistant.is_dangerous_command('rm -rf /'))
        self.assertTrue(self.assistant.is_dangerous_command('dd if=/dev/zero of=/dev/sda'))
        self.assertFalse(self.assistant.is_dangerous_command('ls -la'))
        self.assertFalse(self.assistant.is_dangerous_command('cat file.txt'))
    
    def test_natural_language_translation(self):
        """Test natural language to command translation"""
        # Test basic translations
        self.assertEqual(self.assistant.translate_natural_language('list files'), 'ls -la')
        self.assertEqual(self.assistant.translate_natural_language('show files'), 'ls -la')
        self.assertEqual(self.assistant.translate_natural_language('current directory'), 'pwd')
        self.assertEqual(self.assistant.translate_natural_language('where am i'), 'pwd')
        self.assertEqual(self.assistant.translate_natural_language('disk space'), 'df -h')
        self.assertEqual(self.assistant.translate_natural_language('memory usage'), 'free -h')
        self.assertEqual(self.assistant.translate_natural_language('running processes'), 'ps aux')
    
    def test_command_explanation(self):
        """Test command explanation"""
        self.assertEqual(self.assistant.explain_command('ls'), 'List directory contents')
        self.assertEqual(self.assistant.explain_command('ls -la'), 'List all files with detailed information')
        self.assertEqual(self.assistant.explain_command('pwd'), 'Print current working directory')
        self.assertEqual(self.assistant.explain_command('unknown_command'), 'Command: unknown_command')
    
    def test_get_context(self):
        """Test context gathering"""
        context = self.assistant.get_context()
        self.assertIn('cwd', context)
        self.assertIn('user', context)
        self.assertIn('shell', context)
        self.assertIn('recent_commands', context)
        self.assertIn('directory_contents', context)
    
    @patch('subprocess.run')
    def test_execute_command_success(self, mock_run):
        """Test successful command execution"""
        mock_run.return_value = MagicMock(returncode=0, stdout='output', stderr='')
        
        result = self.assistant.execute_command('ls', confirm=False)
        self.assertTrue(result)
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_run):
        """Test failed command execution"""
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='error')
        
        result = self.assistant.execute_command('invalid_command', confirm=False)
        self.assertFalse(result)
        mock_run.assert_called_once()
    
    def test_history_management(self):
        """Test command history management"""
        # Add some commands to history
        self.assistant.history = [
            {'query': 'test1', 'command': 'ls', 'success': True},
            {'query': 'test2', 'command': 'pwd', 'success': True}
        ]
        
        # Test history saving and loading
        self.assistant.save_history()
        self.assistant.load_history()
        
        self.assertEqual(len(self.assistant.history), 2)
        self.assertEqual(self.assistant.history[0]['command'], 'ls')
        self.assertEqual(self.assistant.history[1]['command'], 'pwd')


if __name__ == '__main__':
    unittest.main()