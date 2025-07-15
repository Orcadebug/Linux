#!/usr/bin/env python3
"""
System Agent - Hardware monitoring, system diagnostics, and performance optimization
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
import signal

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

from .base_agent import BaseAgent, AgentMessage, MessageType, AgentState


class SystemMetrics:
    """System metrics data structure"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.cpu_percent = 0.0
        self.memory_percent = 0.0
        self.disk_percent = 0.0
        self.load_avg = (0.0, 0.0, 0.0)
        self.network_sent = 0
        self.network_recv = 0
        self.process_count = 0
        self.boot_time = 0
        self.gpu_metrics = []
        self.top_processes = []
        self.temperature = {}
        self.battery = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'load_avg': self.load_avg,
            'network_sent': self.network_sent,
            'network_recv': self.network_recv,
            'process_count': self.process_count,
            'boot_time': self.boot_time,
            'gpu_metrics': self.gpu_metrics,
            'top_processes': self.top_processes,
            'temperature': self.temperature,
            'battery': self.battery
        }


class SystemAgent(BaseAgent):
    """Agent for system monitoring and health analysis"""
    
    def __init__(self, agent_id: str, security_manager, config: Dict):
        super().__init__(agent_id, security_manager, config)
        self.name = "System Agent"
        self.description = "Monitors hardware, analyzes system performance, and detects anomalies"
        
        # Monitoring configuration
        self.monitoring_config = {
            "cpu_threshold": config.get('cpu_threshold', 80.0),
            "memory_threshold": config.get('memory_threshold', 85.0),
            "disk_threshold": config.get('disk_threshold', 90.0),
            "network_threshold": config.get('network_threshold', 100.0),  # MB/s
            "check_interval": config.get('check_interval', 30),  # seconds
            "anomaly_detection": config.get('anomaly_detection', True),
            "alert_cooldown": config.get('alert_cooldown', 300),  # seconds
            "history_size": config.get('history_size', 1000)
        }
        
        # Monitoring state
        self.metrics_history = []
        self.last_network_stats = None
        self.anomaly_detector = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.last_alerts = {}
        self.monitoring_active = False
        self.monitoring_task = None
        
        # System baseline
        self.baseline_metrics = None
        self.baseline_established = False
        
        self.logger.info("System Agent initialized with monitoring capabilities")
    
    async def start_monitoring(self):
        """Start continuous system monitoring"""
        if self.monitoring_active:
            return {"status": "already_running"}
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("System monitoring started")
        return {"status": "started", "interval": self.monitoring_config["check_interval"]}
    
    async def stop_monitoring(self):
        """Stop continuous system monitoring"""
        if not self.monitoring_active:
            return {"status": "already_stopped"}
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("System monitoring stopped")
        return {"status": "stopped"}
    
    async def process_message(self, message: AgentMessage) -> Optional[Dict]:
        """Process system monitoring requests"""
        try:
            if message.type == MessageType.TASK:
                return await self._handle_monitoring_task(message.content)
            elif message.type == MessageType.QUERY:
                return await self._handle_monitoring_query(message.content)
            else:
                return await super().process_message(message)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def _handle_monitoring_task(self, content: Dict) -> Dict:
        """Handle monitoring-related tasks"""
        task_type = content.get('type', 'monitor')
        
        if task_type == 'start_monitoring':
            return await self.start_monitoring()
        
        elif task_type == 'stop_monitoring':
            return await self.stop_monitoring()
        
        elif task_type == 'system_scan':
            return await self._perform_system_scan()
        
        elif task_type == 'performance_analysis':
            duration = content.get('duration', 300)  # 5 minutes default
            return await self._analyze_performance(duration)
        
        elif task_type == 'health_check':
            return await self._perform_health_check()
        
        elif task_type == 'optimize_system':
            return await self._suggest_optimizations()
        
        else:
            return {"error": f"Unknown task type: {task_type}", "status": "failed"}
    
    async def _handle_monitoring_query(self, content: Dict) -> Dict:
        """Handle queries about system status"""
        query_type = content.get('type', 'current_status')
        
        if query_type == 'current_status':
            return await self._get_current_status()
        
        elif query_type == 'metrics_history':
            hours = content.get('hours', 1)
            return await self._get_metrics_history(hours)
        
        elif query_type == 'alerts':
            return await self._get_recent_alerts()
        
        elif query_type == 'processes':
            return await self._get_process_info()
        
        elif query_type == 'system_info':
            return await self._get_system_info()
        
        elif query_type == 'anomalies':
            return await self._get_anomaly_report()
        
        else:
            return {"error": f"Unknown query type: {query_type}", "status": "failed"}
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.monitoring_active:
                # Collect metrics
                metrics = await self._collect_system_metrics()
                
                # Store in history
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.monitoring_config["history_size"]:
                    self.metrics_history.pop(0)
                
                # Establish baseline if needed
                if not self.baseline_established and len(self.metrics_history) >= 10:
                    await self._establish_baseline()
                
                # Check thresholds and generate alerts
                alerts = await self._check_thresholds(metrics)
                for alert in alerts:
                    await self._handle_alert(alert)
                
                # Anomaly detection
                if (self.monitoring_config["anomaly_detection"] and 
                    SKLEARN_AVAILABLE and 
                    len(self.metrics_history) >= 50):
                    anomaly = await self._detect_anomalies(metrics)
                    if anomaly:
                        await self._handle_alert(anomaly)
                
                # Wait for next check
                await asyncio.sleep(self.monitoring_config["check_interval"])
                
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
            self.monitoring_active = False
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        metrics = SystemMetrics()
        
        try:
            # Basic system metrics
            metrics.cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            metrics.memory_percent = memory.percent
            disk = psutil.disk_usage('/')
            metrics.disk_percent = disk.percent
            metrics.load_avg = os.getloadavg()
            metrics.process_count = len(psutil.pids())
            metrics.boot_time = psutil.boot_time()
            
            # Network metrics with rate calculation
            net_io = psutil.net_io_counters()
            if self.last_network_stats:
                time_diff = time.time() - self.last_network_stats['timestamp']
                if time_diff > 0:
                    metrics.network_sent = (net_io.bytes_sent - self.last_network_stats['sent']) / time_diff
                    metrics.network_recv = (net_io.bytes_recv - self.last_network_stats['recv']) / time_diff
            
            self.last_network_stats = {
                'timestamp': time.time(),
                'sent': net_io.bytes_sent,
                'recv': net_io.bytes_recv
            }
            
            # GPU metrics
            if GPU_AVAILABLE:
                metrics.gpu_metrics = await self._get_gpu_metrics()
            
            # Temperature sensors
            metrics.temperature = await self._get_temperature_sensors()
            
            # Battery info
            if hasattr(psutil, 'sensors_battery') and psutil.sensors_battery():
                battery = psutil.sensors_battery()
                metrics.battery = {
                    'percent': battery.percent,
                    'power_plugged': battery.power_plugged,
                    'secsleft': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else -1
                }
            
            # Top processes
            metrics.top_processes = await self._get_top_processes()
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    async def _get_gpu_metrics(self) -> List[Dict]:
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
                    'gpu_memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100 if gpu.memoryTotal > 0 else 0,
                    'gpu_temperature': gpu.temperature
                })
        except Exception as e:
            self.logger.debug(f"Could not get GPU metrics: {e}")
        return gpu_metrics
    
    async def _get_temperature_sensors(self) -> Dict:
        """Get system temperature readings"""
        temperatures = {}
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    temperatures[name] = []
                    for entry in entries:
                        temperatures[name].append({
                            'label': entry.label or 'N/A',
                            'current': entry.current,
                            'high': entry.high,
                            'critical': entry.critical
                        })
        except Exception as e:
            self.logger.debug(f"Could not get temperature sensors: {e}")
        return temperatures
    
    async def _get_top_processes(self, limit: int = 10) -> List[Dict]:
        """Get top processes by resource usage"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 0 or proc_info['memory_percent'] > 0:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage and limit results
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            return processes[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting top processes: {e}")
        return []
    
    async def _check_thresholds(self, metrics: SystemMetrics) -> List[Dict]:
        """Check if metrics exceed configured thresholds"""
        alerts = []
        current_time = time.time()
        
        # CPU threshold
        if metrics.cpu_percent > self.monitoring_config['cpu_threshold']:
            if self._should_alert('cpu_high', current_time):
                alerts.append({
                    'type': 'cpu_high',
                    'severity': 'warning',
                    'value': metrics.cpu_percent,
                    'threshold': self.monitoring_config['cpu_threshold'],
                    'message': f"High CPU usage: {metrics.cpu_percent:.1f}%",
                    'timestamp': current_time
                })
        
        # Memory threshold
        if metrics.memory_percent > self.monitoring_config['memory_threshold']:
            if self._should_alert('memory_high', current_time):
                alerts.append({
                    'type': 'memory_high',
                    'severity': 'warning',
                    'value': metrics.memory_percent,
                    'threshold': self.monitoring_config['memory_threshold'],
                    'message': f"High memory usage: {metrics.memory_percent:.1f}%",
                    'timestamp': current_time
                })
        
        # Disk threshold
        if metrics.disk_percent > self.monitoring_config['disk_threshold']:
            if self._should_alert('disk_high', current_time):
                alerts.append({
                    'type': 'disk_high',
                    'severity': 'critical',
                    'value': metrics.disk_percent,
                    'threshold': self.monitoring_config['disk_threshold'],
                    'message': f"High disk usage: {metrics.disk_percent:.1f}%",
                    'timestamp': current_time
                })
        
        # GPU thresholds
        for gpu_metric in metrics.gpu_metrics:
            if gpu_metric['gpu_memory_percent'] > 90:
                gpu_id = gpu_metric['gpu_id']
                if self._should_alert(f'gpu_{gpu_id}_memory_high', current_time):
                    alerts.append({
                        'type': 'gpu_memory_high',
                        'severity': 'warning',
                        'value': gpu_metric['gpu_memory_percent'],
                        'threshold': 90,
                        'message': f"GPU {gpu_id} high memory usage: {gpu_metric['gpu_memory_percent']:.1f}%",
                        'timestamp': current_time
                    })
        
        return alerts
    
    def _should_alert(self, alert_type: str, current_time: float) -> bool:
        """Check if enough time has passed since last alert of this type"""
        if alert_type not in self.last_alerts:
            self.last_alerts[alert_type] = current_time
            return True
        
        time_since_last = current_time - self.last_alerts[alert_type]
        if time_since_last >= self.monitoring_config['alert_cooldown']:
            self.last_alerts[alert_type] = current_time
            return True
        
        return False
    
    async def _establish_baseline(self):
        """Establish baseline metrics for anomaly detection"""
        try:
            if len(self.metrics_history) < 10:
                return
            
            # Calculate baseline from recent history
            recent_metrics = self.metrics_history[-10:]
            
            self.baseline_metrics = {
                'cpu_mean': np.mean([m.cpu_percent for m in recent_metrics]),
                'cpu_std': np.std([m.cpu_percent for m in recent_metrics]),
                'memory_mean': np.mean([m.memory_percent for m in recent_metrics]),
                'memory_std': np.std([m.memory_percent for m in recent_metrics]),
                'process_mean': np.mean([m.process_count for m in recent_metrics]),
                'process_std': np.std([m.process_count for m in recent_metrics])
            }
            
            self.baseline_established = True
            self.logger.info("System baseline established")
            
        except Exception as e:
            self.logger.error(f"Error establishing baseline: {e}")
    
    async def _detect_anomalies(self, metrics: SystemMetrics) -> Optional[Dict]:
        """Detect anomalies using ML if available"""
        try:
            if not SKLEARN_AVAILABLE or len(self.metrics_history) < 50:
                return None
            
            # Prepare feature vector
            features = []
            for m in self.metrics_history[-50:]:
                features.append([
                    m.cpu_percent,
                    m.memory_percent,
                    m.disk_percent,
                    m.process_count,
                    m.load_avg[0] if m.load_avg else 0
                ])
            
            features = np.array(features)
            
            # Initialize or retrain anomaly detector
            if self.anomaly_detector is None or len(self.metrics_history) % 100 == 0:
                self.scaler.fit(features)
                scaled_features = self.scaler.transform(features)
                self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
                self.anomaly_detector.fit(scaled_features)
            
            # Check current metrics
            current_features = np.array([[
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.disk_percent,
                metrics.process_count,
                metrics.load_avg[0] if metrics.load_avg else 0
            ]])
            
            scaled_current = self.scaler.transform(current_features)
            anomaly_score = self.anomaly_detector.decision_function(scaled_current)[0]
            is_anomaly = self.anomaly_detector.predict(scaled_current)[0] == -1
            
            if is_anomaly:
                return {
                    'type': 'system_anomaly',
                    'severity': 'warning',
                    'score': float(anomaly_score),
                    'message': f"System anomaly detected (score: {anomaly_score:.3f})",
                    'timestamp': time.time(),
                    'metrics': {
                        'cpu': metrics.cpu_percent,
                        'memory': metrics.memory_percent,
                        'disk': metrics.disk_percent,
                        'processes': metrics.process_count
                    }
                }
            
        except Exception as e:
            self.logger.error(f"Error in anomaly detection: {e}")
        
        return None
    
    async def _handle_alert(self, alert: Dict):
        """Handle system alerts"""
        self.logger.warning(f"ALERT: {alert['message']}")
        
        # Store alert for later retrieval
        if not hasattr(self, 'recent_alerts'):
            self.recent_alerts = []
        
        self.recent_alerts.append(alert)
        
        # Keep only recent alerts (last 100)
        if len(self.recent_alerts) > 100:
            self.recent_alerts = self.recent_alerts[-100:]
    
    async def _perform_system_scan(self) -> Dict:
        """Perform comprehensive system scan"""
        try:
            scan_results = {
                'timestamp': datetime.now().isoformat(),
                'system_info': await self._get_system_info(),
                'current_metrics': (await self._collect_system_metrics()).to_dict(),
                'disk_usage': await self._get_disk_usage_details(),
                'network_connections': await self._get_network_connections(),
                'running_services': await self._get_running_services(),
                'system_health': await self._assess_system_health()
            }
            
            return {"status": "completed", "scan_results": scan_results}
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _get_system_info(self) -> Dict:
        """Get detailed system information"""
        try:
            uname = os.uname()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            return {
                'hostname': uname.nodename,
                'system': uname.sysname,
                'release': uname.release,
                'version': uname.version,
                'machine': uname.machine,
                'processor': psutil.cpu_count(logical=False),
                'logical_processors': psutil.cpu_count(logical=True),
                'total_memory': psutil.virtual_memory().total,
                'boot_time': boot_time.isoformat(),
                'uptime': str(datetime.now() - boot_time)
            }
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {}
    
    async def _get_disk_usage_details(self) -> Dict:
        """Get detailed disk usage information"""
        disk_info = {}
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.mountpoint] = {
                        'device': partition.device,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    }
                except PermissionError:
                    continue
        except Exception as e:
            self.logger.error(f"Error getting disk usage: {e}")
        return disk_info
    
    async def _get_network_connections(self) -> List[Dict]:
        """Get active network connections"""
        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'ESTABLISHED':
                    connections.append({
                        'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else 'N/A',
                        'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else 'N/A',
                        'status': conn.status,
                        'pid': conn.pid
                    })
        except Exception as e:
            self.logger.error(f"Error getting network connections: {e}")
        return connections
    
    async def _get_running_services(self) -> List[Dict]:
        """Get running system services"""
        services = []
        try:
            for service in psutil.win_service_iter() if hasattr(psutil, 'win_service_iter') else []:
                if service.status() == 'running':
                    services.append({
                        'name': service.name(),
                        'status': service.status(),
                        'start_type': service.start_type()
                    })
        except Exception as e:
            self.logger.debug(f"Could not get services: {e}")
        return services
    
    async def _assess_system_health(self) -> Dict:
        """Assess overall system health"""
        health = {
            'overall_score': 100,
            'issues': [],
            'recommendations': []
        }
        
        try:
            current_metrics = await self._collect_system_metrics()
            
            # CPU health
            if current_metrics.cpu_percent > 80:
                health['overall_score'] -= 20
                health['issues'].append(f"High CPU usage: {current_metrics.cpu_percent:.1f}%")
                health['recommendations'].append("Consider closing unnecessary applications or processes")
            
            # Memory health
            if current_metrics.memory_percent > 85:
                health['overall_score'] -= 25
                health['issues'].append(f"High memory usage: {current_metrics.memory_percent:.1f}%")
                health['recommendations'].append("Close memory-intensive applications or add more RAM")
            
            # Disk health
            if current_metrics.disk_percent > 90:
                health['overall_score'] -= 30
                health['issues'].append(f"Low disk space: {current_metrics.disk_percent:.1f}% used")
                health['recommendations'].append("Clean up unnecessary files or expand storage")
            
            # Load average health
            if current_metrics.load_avg and current_metrics.load_avg[0] > psutil.cpu_count():
                health['overall_score'] -= 15
                health['issues'].append(f"High system load: {current_metrics.load_avg[0]:.2f}")
                health['recommendations'].append("System is overloaded, consider reducing concurrent tasks")
            
            # GPU health
            for gpu in current_metrics.gpu_metrics:
                if gpu['gpu_memory_percent'] > 90:
                    health['overall_score'] -= 10
                    health['issues'].append(f"GPU {gpu['gpu_id']} memory high: {gpu['gpu_memory_percent']:.1f}%")
                    health['recommendations'].append("Close GPU-intensive applications")
            
            # Ensure score doesn't go below 0
            health['overall_score'] = max(0, health['overall_score'])
            
            # Determine health status
            if health['overall_score'] >= 80:
                health['status'] = 'excellent'
            elif health['overall_score'] >= 60:
                health['status'] = 'good'
            elif health['overall_score'] >= 40:
                health['status'] = 'fair'
            else:
                health['status'] = 'poor'
                
        except Exception as e:
            self.logger.error(f"Error assessing system health: {e}")
            health['status'] = 'unknown'
            health['error'] = str(e)
        
        return health
    
    async def _suggest_optimizations(self) -> Dict:
        """Suggest system optimizations based on current state"""
        suggestions = {
            'performance': [],
            'security': [],
            'maintenance': [],
            'priority': 'low'
        }
        
        try:
            current_metrics = await self._collect_system_metrics()
            
            # Performance suggestions
            if current_metrics.cpu_percent > 70:
                suggestions['performance'].append("Consider limiting background processes")
                suggestions['performance'].append("Check for CPU-intensive applications")
                suggestions['priority'] = 'high'
            
            if current_metrics.memory_percent > 80:
                suggestions['performance'].append("Close unused applications to free memory")
                suggestions['performance'].append("Consider upgrading RAM if this is persistent")
                suggestions['priority'] = 'high'
            
            if current_metrics.disk_percent > 80:
                suggestions['maintenance'].append("Run disk cleanup to free space")
                suggestions['maintenance'].append("Consider archiving old files")
                if current_metrics.disk_percent > 90:
                    suggestions['priority'] = 'critical'
            
            # Process-based suggestions
            if len(current_metrics.top_processes) > 0:
                high_cpu_processes = [p for p in current_metrics.top_processes if p['cpu_percent'] > 50]
                if high_cpu_processes:
                    process_names = [p['name'] for p in high_cpu_processes[:3]]
                    suggestions['performance'].append(f"High CPU processes detected: {', '.join(process_names)}")
            
            # GPU suggestions
            for gpu in current_metrics.gpu_metrics:
                if gpu['gpu_memory_percent'] > 85:
                    suggestions['performance'].append(f"GPU {gpu['gpu_id']} memory usage high - consider closing graphics-intensive applications")
            
            # Security suggestions
            suggestions['security'].append("Regularly update system packages")
            suggestions['security'].append("Monitor unusual network activity")
            
            # Maintenance suggestions
            if not suggestions['maintenance']:
                suggestions['maintenance'].append("System maintenance is up to date")
            
            return {"status": "completed", "suggestions": suggestions}
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _get_current_status(self) -> Dict:
        """Get current system status"""
        try:
            metrics = await self._collect_system_metrics()
            health = await self._assess_system_health()
            
            return {
                "status": "success",
                "metrics": metrics.to_dict(),
                "health": health,
                "monitoring_active": self.monitoring_active,
                "baseline_established": self.baseline_established
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _get_metrics_history(self, hours: int) -> Dict:
        """Get metrics history for specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_metrics = [
                m.to_dict() for m in self.metrics_history 
                if m.timestamp >= cutoff_time
            ]
            
            return {
                "status": "success",
                "metrics": filtered_metrics,
                "count": len(filtered_metrics),
                "hours": hours
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _get_recent_alerts(self) -> Dict:
        """Get recent system alerts"""
        try:
            recent_alerts = getattr(self, 'recent_alerts', [])
            return {
                "status": "success",
                "alerts": recent_alerts[-20:],  # Last 20 alerts
                "total_alerts": len(recent_alerts)
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _get_process_info(self) -> Dict:
        """Get detailed process information"""
        try:
            processes = await self._get_top_processes(limit=20)
            return {
                "status": "success",
                "processes": processes,
                "total_processes": len(psutil.pids())
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _get_anomaly_report(self) -> Dict:
        """Get anomaly detection report"""
        try:
            report = {
                "anomaly_detection_enabled": self.monitoring_config["anomaly_detection"] and SKLEARN_AVAILABLE,
                "baseline_established": self.baseline_established,
                "sklearn_available": SKLEARN_AVAILABLE,
                "history_size": len(self.metrics_history),
                "baseline_metrics": self.baseline_metrics
            }
            
            if hasattr(self, 'recent_alerts'):
                anomaly_alerts = [a for a in self.recent_alerts if a.get('type') == 'system_anomaly']
                report['recent_anomalies'] = anomaly_alerts[-10:]  # Last 10 anomalies
            
            return {"status": "success", "report": report}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def get_status(self) -> Dict:
        """Get agent status"""
        status = await super().get_status()
        status.update({
            'monitoring_active': self.monitoring_active,
            'metrics_collected': len(self.metrics_history),
            'baseline_established': self.baseline_established,
            'gpu_available': GPU_AVAILABLE,
            'sklearn_available': SKLEARN_AVAILABLE
        })
        return status
    
    async def cleanup(self):
        """Cleanup agent resources"""
        if self.monitoring_active:
            await self.stop_monitoring()
        await super().cleanup() 