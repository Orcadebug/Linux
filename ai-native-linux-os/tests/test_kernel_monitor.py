#!/usr/bin/env python3
"""
Test suite for AI Kernel Monitor
"""

import unittest
import sys
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kernel_monitor.kernel_monitor import AIKernelMonitor


class TestAIKernelMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = AIKernelMonitor()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_defaults(self):
        """Test loading default configuration"""
        config = self.monitor.load_config(None)
        self.assertIn('cpu_threshold', config)
        self.assertIn('memory_threshold', config)
        self.assertIn('disk_threshold', config)
        self.assertEqual(config['cpu_threshold'], 80.0)
        self.assertEqual(config['memory_threshold'], 85.0)
    
    def test_load_config_custom(self):
        """Test loading custom configuration"""
        config_file = os.path.join(self.temp_dir, 'config.json')
        custom_config = {
            'cpu_threshold': 90.0,
            'memory_threshold': 95.0,
            'check_interval': 10
        }
        
        with open(config_file, 'w') as f:
            json.dump(custom_config, f)
        
        config = self.monitor.load_config(config_file)
        self.assertEqual(config['cpu_threshold'], 90.0)
        self.assertEqual(config['memory_threshold'], 95.0)
        self.assertEqual(config['check_interval'], 10)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('os.getloadavg')
    @patch('psutil.pids')
    @patch('psutil.boot_time')
    def test_get_system_metrics(self, mock_boot_time, mock_pids, mock_loadavg, 
                               mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test system metrics collection"""
        # Mock psutil functions
        mock_cpu_percent.return_value = 50.0
        mock_virtual_memory.return_value = MagicMock(percent=60.0)
        mock_disk_usage.return_value = MagicMock(percent=70.0)
        mock_loadavg.return_value = (1.0, 1.5, 2.0)
        mock_pids.return_value = [1, 2, 3, 4, 5]
        mock_boot_time.return_value = 1640995200.0
        
        metrics = self.monitor.get_system_metrics()
        
        self.assertIn('timestamp', metrics)
        self.assertEqual(metrics['cpu_percent'], 50.0)
        self.assertEqual(metrics['memory_percent'], 60.0)
        self.assertEqual(metrics['disk_percent'], 70.0)
        self.assertEqual(metrics['load_avg'], (1.0, 1.5, 2.0))
        self.assertEqual(metrics['process_count'], 5)
    
    def test_check_thresholds_normal(self):
        """Test threshold checking with normal values"""
        metrics = {
            'cpu_percent': 50.0,
            'memory_percent': 60.0,
            'disk_percent': 70.0,
            'load_avg': (1.0, 1.5, 2.0)
        }
        
        alerts = self.monitor.check_thresholds(metrics)
        self.assertEqual(len(alerts), 0)
    
    def test_check_thresholds_high_cpu(self):
        """Test threshold checking with high CPU usage"""
        metrics = {
            'cpu_percent': 90.0,
            'memory_percent': 60.0,
            'disk_percent': 70.0,
            'load_avg': (1.0, 1.5, 2.0)
        }
        
        alerts = self.monitor.check_thresholds(metrics)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'cpu_high')
        self.assertEqual(alerts[0]['severity'], 'warning')
    
    def test_check_thresholds_high_memory(self):
        """Test threshold checking with high memory usage"""
        metrics = {
            'cpu_percent': 50.0,
            'memory_percent': 90.0,
            'disk_percent': 70.0,
            'load_avg': (1.0, 1.5, 2.0)
        }
        
        alerts = self.monitor.check_thresholds(metrics)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'memory_high')
        self.assertEqual(alerts[0]['severity'], 'warning')
    
    def test_check_thresholds_high_disk(self):
        """Test threshold checking with high disk usage"""
        metrics = {
            'cpu_percent': 50.0,
            'memory_percent': 60.0,
            'disk_percent': 95.0,
            'load_avg': (1.0, 1.5, 2.0)
        }
        
        alerts = self.monitor.check_thresholds(metrics)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'disk_high')
        self.assertEqual(alerts[0]['severity'], 'critical')
    
    @patch('psutil.cpu_count')
    def test_check_thresholds_high_load(self, mock_cpu_count):
        """Test threshold checking with high system load"""
        mock_cpu_count.return_value = 4
        
        metrics = {
            'cpu_percent': 50.0,
            'memory_percent': 60.0,
            'disk_percent': 70.0,
            'load_avg': (1.0, 10.0, 2.0)  # High 5-minute load average
        }
        
        alerts = self.monitor.check_thresholds(metrics)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'load_high')
        self.assertEqual(alerts[0]['severity'], 'warning')
    
    def test_generate_suggestions(self):
        """Test suggestion generation"""
        alerts = [
            {'type': 'cpu_high', 'value': 90.0, 'severity': 'warning'},
            {'type': 'memory_high', 'value': 95.0, 'severity': 'warning'},
            {'type': 'disk_high', 'value': 98.0, 'severity': 'critical'}
        ]
        
        suggestions = self.monitor.generate_suggestions(alerts)
        
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(any('top' in suggestion for suggestion in suggestions))
        self.assertTrue(any('memory' in suggestion.lower() for suggestion in suggestions))
        self.assertTrue(any('disk' in suggestion.lower() for suggestion in suggestions))
    
    def test_update_anomaly_detector(self):
        """Test anomaly detector update"""
        # Add some metrics to history
        for i in range(10):
            metrics = {
                'cpu_percent': 50.0 + i,
                'memory_percent': 60.0 + i,
                'disk_percent': 70.0 + i,
                'load_avg': (1.0, 1.5, 2.0),
                'process_count': 100 + i
            }
            self.monitor.update_anomaly_detector(metrics)
        
        # Check that history is being maintained
        self.assertEqual(len(self.monitor.metrics_history), 10)
        
        # Test with normal metrics
        normal_metrics = {
            'cpu_percent': 55.0,
            'memory_percent': 65.0,
            'disk_percent': 75.0,
            'load_avg': (1.0, 1.5, 2.0),
            'process_count': 105
        }
        
        result = self.monitor.update_anomaly_detector(normal_metrics)
        # Should return None for normal metrics with insufficient history
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()