#!/usr/bin/env python3
"""
AI Kernel Monitor - Intelligent system monitoring with anomaly detection
"""

import os
import sys
import time
import json
import logging
import psutil
import threading
import signal
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import GPUtil


class AIKernelMonitor:
    def __init__(self, config_file=None):
        self.config = self.load_config(config_file)
        self.running = False
        self.metrics_history = []
        self.max_history = 1000
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.setup_logging()
        self.setup_signal_handlers()
        
    def load_config(self, config_file):
        """Load configuration from file or use defaults"""
        default_config = {
            "cpu_threshold": 80.0,
            "memory_threshold": 85.0,
            "disk_threshold": 90.0,
            "network_threshold": 100.0,  # MB/s
            "check_interval": 5,  # seconds
            "anomaly_detection": True,
            "alert_cooldown": 300,  # seconds
            "log_file": "/var/log/kernel_monitor.log"
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['log_file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AIKernelMonitor')
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def get_gpu_metrics(self):
        """Collect GPU metrics"""
        gpu_metrics = []
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_metrics.append({
                    'gpu_id': gpu.id,
                    'gpu_name': gpu.name,
                    'gpu_load': gpu.load * 100,
                    'gpu_memory_used': gpu.memoryUsed,
                    'gpu_memory_total': gpu.memoryTotal,
                    'gpu_memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100,
                    'gpu_temperature': gpu.temperature
                })
        except Exception as e:
            self.logger.warning(f"Could not get GPU metrics: {e}")
        return gpu_metrics
    
    def get_system_metrics(self):
        """Collect current system metrics including GPU"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_avg': os.getloadavg(),
            'network_sent': 0,
            'network_recv': 0,
            'process_count': len(psutil.pids()),
            'boot_time': psutil.boot_time(),
            'gpu_metrics': self.get_gpu_metrics()  # Add GPU metrics
        }
        
        # Get network statistics
        try:
            net_io = psutil.net_io_counters()
            metrics['network_sent'] = net_io.bytes_sent
            metrics['network_recv'] = net_io.bytes_recv
        except:
            pass
        
        # Get top processes by CPU usage
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 0:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            metrics['top_processes'] = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
        except:
            metrics['top_processes'] = []
        
        return metrics
    
    def check_thresholds(self, metrics):
        """Check if any metrics exceed thresholds"""
        alerts = []
        
        if metrics['cpu_percent'] > self.config['cpu_threshold']:
            alerts.append({
                'type': 'cpu_high',
                'value': metrics['cpu_percent'],
                'threshold': self.config['cpu_threshold'],
                'severity': 'warning',
                'message': f"High CPU usage: {metrics['cpu_percent']:.1f}%"
            })
        
        if metrics['memory_percent'] > self.config['memory_threshold']:
            alerts.append({
                'type': 'memory_high',
                'value': metrics['memory_percent'],
                'threshold': self.config['memory_threshold'],
                'severity': 'warning',
                'message': f"High memory usage: {metrics['memory_percent']:.1f}%"
            })
        
        if metrics['disk_percent'] > self.config['disk_threshold']:
            alerts.append({
                'type': 'disk_high',
                'value': metrics['disk_percent'],
                'threshold': self.config['disk_threshold'],
                'severity': 'critical',
                'message': f"High disk usage: {metrics['disk_percent']:.1f}%"
            })
        
        # Check load average
        load_avg_5min = metrics['load_avg'][1]
        cpu_count = psutil.cpu_count()
        if load_avg_5min > cpu_count * 2:
            alerts.append({
                'type': 'load_high',
                'value': load_avg_5min,
                'threshold': cpu_count * 2,
                'severity': 'warning',
                'message': f"High system load: {load_avg_5min:.2f} (CPU count: {cpu_count})"
            })
        
        return alerts
    
    def check_gpu_thresholds(self, gpu_metrics):
        """Check GPU-specific thresholds"""
        alerts = []
        for gpu in gpu_metrics:
            if gpu['gpu_load'] > 95:
                alerts.append({
                    'type': 'gpu_high_utilization',
                    'gpu_id': gpu['gpu_id'],
                    'value': gpu['gpu_load'],
                    'threshold': 95,
                    'severity': 'warning',
                    'message': f"GPU {gpu['gpu_id']} high utilization: {gpu['gpu_load']:.1f}%"
                })
            if gpu['gpu_memory_percent'] > 90:
                alerts.append({
                    'type': 'gpu_memory_high',
                    'gpu_id': gpu['gpu_id'],
                    'value': gpu['gpu_memory_percent'],
                    'threshold': 90,
                    'severity': 'critical',
                    'message': f"GPU {gpu['gpu_id']} memory high: {gpu['gpu_memory_percent']:.1f}%"
                })
            if gpu['gpu_temperature'] > 80:
                alerts.append({
                    'type': 'gpu_temperature_high',
                    'gpu_id': gpu['gpu_id'],
                    'value': gpu['gpu_temperature'],
                    'threshold': 80,
                    'severity': 'warning',
                    'message': f"GPU {gpu['gpu_id']} temperature high: {gpu['gpu_temperature']}°C"
                })
        return alerts
    
    def update_anomaly_detector(self, metrics):
        """Update anomaly detection model with new metrics"""
        if not self.config['anomaly_detection']:
            return
        
        # Extract numeric features for anomaly detection
        features = [
            metrics['cpu_percent'],
            metrics['memory_percent'],
            metrics['disk_percent'],
            metrics['load_avg'][0],
            metrics['process_count']
        ]
        
        self.metrics_history.append(features)
        
        # Keep only recent history
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
        
        # Train anomaly detector if we have enough data
        if len(self.metrics_history) >= 100:
            try:
                X = np.array(self.metrics_history)
                X_scaled = self.scaler.fit_transform(X)
                
                if self.anomaly_detector is None:
                    self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
                
                self.anomaly_detector.fit(X_scaled)
                
                # Check if current metrics are anomalous
                current_features = np.array([features])
                current_scaled = self.scaler.transform(current_features)
                anomaly_score = self.anomaly_detector.decision_function(current_scaled)[0]
                is_anomaly = self.anomaly_detector.predict(current_scaled)[0] == -1
                
                if is_anomaly:
                    self.logger.warning(f"Anomaly detected! Score: {anomaly_score:.3f}")
                    return {
                        'type': 'anomaly',
                        'score': anomaly_score,
                        'severity': 'warning',
                        'message': f"System behavior anomaly detected (score: {anomaly_score:.3f})"
                    }
            except Exception as e:
                self.logger.error(f"Error in anomaly detection: {e}")
        
        return None
    
    def generate_suggestions(self, alerts):
        """Generate suggestions for addressing alerts"""
        suggestions = []
        
        for alert in alerts:
            if alert['type'] == 'cpu_high':
                suggestions.extend([
                    "Check top CPU-consuming processes with 'top' or 'htop'",
                    "Consider killing unnecessary processes",
                    "Check for runaway processes or infinite loops"
                ])
            elif alert['type'] == 'memory_high':
                suggestions.extend([
                    "Check memory usage with 'free -h'",
                    "Identify memory-hungry processes with 'ps aux --sort=-resident'",
                    "Consider restarting services that may have memory leaks"
                ])
            elif alert['type'] == 'disk_high':
                suggestions.extend([
                    "Check disk usage with 'df -h'",
                    "Find large files with 'find / -type f -size +100M'",
                    "Clean up log files and temporary files",
                    "Consider moving data to external storage"
                ])
            elif alert['type'] == 'load_high':
                suggestions.extend([
                    "Check system load with 'uptime'",
                    "Identify I/O-bound processes with 'iotop'",
                    "Check for disk I/O issues with 'iostat'"
                ])
        
        return list(set(suggestions))  # Remove duplicates
    
    def generate_ai_ml_suggestions(self, alerts):
        """Generate AI/ML specific suggestions"""
        suggestions = []
        for alert in alerts:
            if alert['type'] == 'gpu_memory_high':
                suggestions.append({
                    'alert_type': alert['type'],
                    'suggestion': f"GPU {alert['gpu_id']} memory is high. Consider:\n- Reducing batch size\n- Using gradient accumulation\n- Enabling mixed precision training\n- Clearing GPU cache: torch.cuda.empty_cache()",
                    'commands': [
                        "nvidia-smi pmon -c 1",
                        "python3 -c 'import torch; torch.cuda.empty_cache(); print(\"GPU cache cleared\")'"
                    ]
                })
            elif alert['type'] == 'gpu_high_utilization':
                suggestions.append({
                    'alert_type': alert['type'],
                    'suggestion': f"GPU {alert['gpu_id']} is at high utilization. This might be normal during training.",
                    'commands': [
                        "nvidia-smi pmon -c 1"
                    ]
                })
            elif alert['type'] == 'cpu_high' and any('python' in str(proc.get('name', '')) for proc in alert.get('top_processes', [])):
                suggestions.append({
                    'alert_type': alert['type'],
                    'suggestion': "High CPU usage detected with Python processes. Consider:\n- Using more CPU workers for data loading\n- Optimizing data preprocessing\n- Moving computation to GPU",
                    'commands': [
                        "ps aux | grep python",
                        "htop"
                    ]
                })
        return suggestions
    
    def handle_alerts(self, alerts, suggestions):
        """Handle system alerts"""
        for alert in alerts:
            self.logger.warning(f"ALERT: {alert['message']}")
            
            # Log to quest log if available
            self.log_to_quest_log(alert)
        
        if suggestions:
            self.logger.info("Suggestions:")
            for suggestion in suggestions:
                self.logger.info(f"  - {suggestion}")
    
    def log_to_quest_log(self, alert):
        """Log alert to quest log system"""
        try:
            # This would integrate with the quest log daemon
            # For now, we'll just log to a file
            quest_log_file = Path.home() / ".kernel_monitor_alerts.json"
            
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'alert': alert
            }
            
            alerts_history = []
            if quest_log_file.exists():
                try:
                    with open(quest_log_file, 'r') as f:
                        alerts_history = json.load(f)
                except:
                    alerts_history = []
            
            alerts_history.append(alert_data)
            
            # Keep only recent alerts
            if len(alerts_history) > 1000:
                alerts_history = alerts_history[-1000:]
            
            with open(quest_log_file, 'w') as f:
                json.dump(alerts_history, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Error logging to quest log: {e}")
    
    def start(self):
        """Start the monitoring daemon"""
        self.logger.info("Starting AI Kernel Monitor...")
        self.running = True
        
        last_alert_time = {}
        
        while self.running:
            try:
                # Collect metrics
                metrics = self.get_system_metrics()
                
                # Check thresholds
                alerts = self.check_thresholds(metrics)
                
                # Check GPU thresholds
                gpu_alerts = self.check_gpu_thresholds(metrics['gpu_metrics'])
                alerts.extend(gpu_alerts)
                
                # Check for anomalies
                anomaly_alert = self.update_anomaly_detector(metrics)
                if anomaly_alert:
                    alerts.append(anomaly_alert)
                
                # Handle alerts with cooldown
                current_time = time.time()
                filtered_alerts = []
                
                for alert in alerts:
                    alert_key = alert['type']
                    if (alert_key not in last_alert_time or 
                        current_time - last_alert_time[alert_key] > self.config['alert_cooldown']):
                        filtered_alerts.append(alert)
                        last_alert_time[alert_key] = current_time
                
                if filtered_alerts:
                    suggestions = self.generate_suggestions(filtered_alerts)
                    ai_ml_suggestions = self.generate_ai_ml_suggestions(filtered_alerts)
                    self.handle_alerts(filtered_alerts, suggestions + ai_ml_suggestions)
                
                # Wait for next check
                time.sleep(self.config['check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
        
        self.logger.info("AI Kernel Monitor stopped")


def main():
    """Main entry point"""
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    monitor = AIKernelMonitor(config_file)
    monitor.start()


if __name__ == '__main__':
    main()