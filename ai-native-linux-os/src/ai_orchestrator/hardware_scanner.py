#!/usr/bin/env python3
"""
Hardware Scanner - Scans system hardware and determines optimal LLM configuration
"""

import asyncio
import json
import logging
import platform
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class HardwareInfo:
    def __init__(self):
        self.cpu_count = 0
        self.cpu_logical_count = 0
        self.cpu_frequency = 0.0
        self.cpu_model = ""
        self.ram_total_gb = 0.0
        self.ram_available_gb = 0.0
        self.gpus = []
        self.storage_total_gb = 0.0
        self.storage_free_gb = 0.0
        self.network_connected = False
        self.os_info = {}
        self.cuda_version = None
        self.opencl_available = False
        
    def to_dict(self) -> Dict:
        return {
            'cpu': {
                'count': self.cpu_count,
                'logical_count': self.cpu_logical_count,
                'frequency_mhz': self.cpu_frequency,
                'model': self.cpu_model
            },
            'memory': {
                'total_gb': self.ram_total_gb,
                'available_gb': self.ram_available_gb
            },
            'gpus': self.gpus,
            'storage': {
                'total_gb': self.storage_total_gb,
                'free_gb': self.storage_free_gb
            },
            'network': {
                'connected': self.network_connected
            },
            'os': self.os_info,
            'compute': {
                'cuda_version': self.cuda_version,
                'opencl_available': self.opencl_available
            }
        }


class LLMCapability:
    def __init__(self, level: str, models: List[str], min_ram_gb: float, 
                 min_vram_gb: float = 0, requires_gpu: bool = False):
        self.level = level
        self.models = models
        self.min_ram_gb = min_ram_gb
        self.min_vram_gb = min_vram_gb
        self.requires_gpu = requires_gpu
        
    def to_dict(self) -> Dict:
        return {
            'level': self.level,
            'models': self.models,
            'min_ram_gb': self.min_ram_gb,
            'min_vram_gb': self.min_vram_gb,
            'requires_gpu': self.requires_gpu
        }


class HardwareScanner:
    def __init__(self):
        self.logger = logging.getLogger("HardwareScanner")
        
        # Define LLM capability levels
        self.llm_capabilities = {
            'HIGH': LLMCapability(
                level='HIGH',
                models=['llama3', 'codellama:7b', 'mistral:7b'],
                min_ram_gb=16.0,
                min_vram_gb=8.0,
                requires_gpu=False
            ),
            'MEDIUM': LLMCapability(
                level='MEDIUM', 
                models=['phi3:3.8b', 'llama3:8b', 'gemma:2b'],
                min_ram_gb=8.0,
                min_vram_gb=4.0,
                requires_gpu=False
            ),
            'LOW': LLMCapability(
                level='LOW',
                models=['phi3:1.4b', 'tinyllama:1.1b', 'qwen2:0.5b'],
                min_ram_gb=4.0,
                min_vram_gb=2.0,
                requires_gpu=False
            ),
            'FALLBACK': LLMCapability(
                level='FALLBACK',
                models=['rule-based'],  # No actual LLM
                min_ram_gb=2.0,
                requires_gpu=False
            )
        }
        
        # Agent-specific model preferences
        self.agent_model_preferences = {
            'system_agent': {
                'HIGH': 'llama3',
                'MEDIUM': 'phi3:3.8b', 
                'LOW': 'tinyllama:1.1b',
                'FALLBACK': 'rule-based'
            },
            'file_management_agent': {
                'HIGH': 'codellama:7b',
                'MEDIUM': 'phi3:3.8b',
                'LOW': 'rule-based',
                'FALLBACK': 'rule-based'
            },
            'software_install_agent': {
                'HIGH': 'llama3',
                'MEDIUM': 'phi3:3.8b',
                'LOW': 'rule-based',
                'FALLBACK': 'rule-based'
            },
            'shell_assistant_agent': {
                'HIGH': 'mistral:7b',
                'MEDIUM': 'phi3:3.8b',
                'LOW': 'tinyllama:1.1b',
                'FALLBACK': 'rule-based'
            },
            'activity_tracker_agent': {
                'HIGH': 'phi3:3.8b',
                'MEDIUM': 'tinyllama:1.1b',
                'LOW': 'rule-based',
                'FALLBACK': 'rule-based'
            }
        }
    
    async def scan_system(self) -> Dict:
        """Comprehensive system hardware scan"""
        self.logger.info("Starting hardware scan...")
        
        hardware_info = HardwareInfo()
        
        # Scan components in parallel
        tasks = [
            self._scan_cpu(hardware_info),
            self._scan_memory(hardware_info),
            self._scan_gpu(hardware_info),
            self._scan_storage(hardware_info),
            self._scan_network(hardware_info),
            self._scan_os(hardware_info),
            self._scan_compute_capabilities(hardware_info)
        ]
        
        await asyncio.gather(*tasks)
        
        # Determine optimal LLM configuration
        llm_config = self._determine_llm_config(hardware_info)
        
        result = {
            'hardware': hardware_info.to_dict(),
            'llm_config': llm_config,
            'scan_timestamp': time.time()
        }
        
        self.logger.info(f"Hardware scan complete: {llm_config['overall_level']} capability")
        return result
    
    async def _scan_cpu(self, hw_info: HardwareInfo):
        """Scan CPU information"""
        try:
            hw_info.cpu_count = psutil.cpu_count(logical=False)
            hw_info.cpu_logical_count = psutil.cpu_count(logical=True)
            
            # Get CPU frequency
            freq = psutil.cpu_freq()
            if freq:
                hw_info.cpu_frequency = freq.current
            
            # Get CPU model (Linux-specific)
            if platform.system() == "Linux":
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if line.startswith('model name'):
                                hw_info.cpu_model = line.split(':')[1].strip()
                                break
                except Exception:
                    pass
            
            if not hw_info.cpu_model:
                hw_info.cpu_model = platform.processor()
                
        except Exception as e:
            self.logger.error(f"CPU scan failed: {e}")
    
    async def _scan_memory(self, hw_info: HardwareInfo):
        """Scan memory information"""
        try:
            memory = psutil.virtual_memory()
            hw_info.ram_total_gb = memory.total / (1024**3)
            hw_info.ram_available_gb = memory.available / (1024**3)
        except Exception as e:
            self.logger.error(f"Memory scan failed: {e}")
    
    async def _scan_gpu(self, hw_info: HardwareInfo):
        """Scan GPU information"""
        try:
            if GPUTIL_AVAILABLE:
                gpus = GPUtil.getGPUs()
                for gpu in gpus:
                    gpu_info = {
                        'id': gpu.id,
                        'name': gpu.name,
                        'memory_total_mb': gpu.memoryTotal,
                        'memory_free_mb': gpu.memoryFree,
                        'memory_used_mb': gpu.memoryUsed,
                        'utilization_percent': gpu.load * 100,
                        'temperature_c': gpu.temperature,
                        'driver_version': getattr(gpu, 'driver', 'unknown')
                    }
                    hw_info.gpus.append(gpu_info)
            else:
                # Fallback: try nvidia-smi
                try:
                    result = subprocess.run(
                        ['nvidia-smi', '--query-gpu=name,memory.total,memory.free,driver_version', 
                         '--format=csv,noheader,nounits'],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                parts = line.split(', ')
                                if len(parts) >= 3:
                                    gpu_info = {
                                        'name': parts[0],
                                        'memory_total_mb': int(parts[1]),
                                        'memory_free_mb': int(parts[2]),
                                        'driver_version': parts[3] if len(parts) > 3 else 'unknown'
                                    }
                                    hw_info.gpus.append(gpu_info)
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"GPU scan failed: {e}")
    
    async def _scan_storage(self, hw_info: HardwareInfo):
        """Scan storage information"""
        try:
            usage = psutil.disk_usage('/')
            hw_info.storage_total_gb = usage.total / (1024**3)
            hw_info.storage_free_gb = usage.free / (1024**3)
        except Exception as e:
            self.logger.error(f"Storage scan failed: {e}")
    
    async def _scan_network(self, hw_info: HardwareInfo):
        """Check network connectivity"""
        try:
            # Simple connectivity check
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                capture_output=True, timeout=5
            )
            hw_info.network_connected = (result.returncode == 0)
        except Exception:
            hw_info.network_connected = False
    
    async def _scan_os(self, hw_info: HardwareInfo):
        """Scan OS information"""
        try:
            hw_info.os_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'architecture': platform.architecture()[0]
            }
        except Exception as e:
            self.logger.error(f"OS scan failed: {e}")
    
    async def _scan_compute_capabilities(self, hw_info: HardwareInfo):
        """Scan compute capabilities (CUDA, OpenCL)"""
        try:
            # Check CUDA
            try:
                result = subprocess.run(
                    ['nvcc', '--version'], 
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    version_match = re.search(r'release (\d+\.\d+)', result.stdout)
                    if version_match:
                        hw_info.cuda_version = version_match.group(1)
            except Exception:
                pass
            
            # Check OpenCL (simplified)
            try:
                result = subprocess.run(
                    ['clinfo'], 
                    capture_output=True, text=True, timeout=10
                )
                hw_info.opencl_available = (result.returncode == 0)
            except Exception:
                pass
                
        except Exception as e:
            self.logger.error(f"Compute capabilities scan failed: {e}")
    
    def _determine_llm_config(self, hw_info: HardwareInfo) -> Dict:
        """Determine optimal LLM configuration based on hardware"""
        
        # Determine overall capability level
        if hw_info.ram_total_gb >= 32 and hw_info.gpus:
            # High-end system with GPU
            overall_level = 'HIGH'
        elif hw_info.ram_total_gb >= 16:
            # Medium-high system
            overall_level = 'HIGH' if hw_info.gpus else 'MEDIUM'
        elif hw_info.ram_total_gb >= 8:
            # Medium system
            overall_level = 'MEDIUM'
        elif hw_info.ram_total_gb >= 4:
            # Low-end system
            overall_level = 'LOW'
        else:
            # Very low resources
            overall_level = 'FALLBACK'
        
        # Adjust based on available RAM (conservative approach)
        available_ratio = hw_info.ram_available_gb / max(hw_info.ram_total_gb, 1)
        if available_ratio < 0.5:  # Less than 50% RAM available
            if overall_level == 'HIGH':
                overall_level = 'MEDIUM'
            elif overall_level == 'MEDIUM':
                overall_level = 'LOW'
        
        # Generate agent-specific configurations
        agent_configs = {}
        for agent_name, preferences in self.agent_model_preferences.items():
            agent_level = self._determine_agent_level(agent_name, overall_level, hw_info)
            model = preferences.get(agent_level, 'rule-based')
            
            agent_configs[agent_name] = {
                'level': agent_level,
                'model': model,
                'use_gpu': len(hw_info.gpus) > 0 and agent_level in ['HIGH', 'MEDIUM'],
                'max_context_length': self._get_context_length(agent_level),
                'temperature': self._get_temperature(agent_name),
                'fallback_to_rules': agent_level == 'FALLBACK'
            }
        
        return {
            'overall_level': overall_level,
            'agent_configs': agent_configs,
            'recommended_models': self._get_recommended_models(overall_level),
            'gpu_acceleration': len(hw_info.gpus) > 0,
            'parallel_agents': self._calculate_parallel_capacity(hw_info),
            'estimated_performance': self._estimate_performance(overall_level, hw_info)
        }
    
    def _determine_agent_level(self, agent_name: str, overall_level: str, hw_info: HardwareInfo) -> str:
        """Determine specific capability level for an agent"""
        
        # Agent-specific adjustments
        agent_priorities = {
            'software_install_agent': 1.2,  # Needs more resources for complex decisions
            'system_agent': 1.1,           # Needs good analysis capabilities
            'shell_assistant_agent': 1.0,   # Standard
            'file_management_agent': 0.8,   # Can work with less
            'activity_tracker_agent': 0.6   # Mostly pattern matching
        }
        
        priority = agent_priorities.get(agent_name, 1.0)
        
        # Adjust level based on priority and available resources
        levels = ['FALLBACK', 'LOW', 'MEDIUM', 'HIGH']
        current_index = levels.index(overall_level)
        
        if priority > 1.1 and current_index < len(levels) - 1:
            # High priority agents get boosted if possible
            return levels[min(current_index + 1, len(levels) - 1)]
        elif priority < 0.8 and current_index > 0:
            # Low priority agents can be downgraded
            return levels[max(current_index - 1, 0)]
        
        return overall_level
    
    def _get_context_length(self, level: str) -> int:
        """Get appropriate context length for capability level"""
        context_lengths = {
            'HIGH': 8192,
            'MEDIUM': 4096,
            'LOW': 2048,
            'FALLBACK': 512
        }
        return context_lengths.get(level, 2048)
    
    def _get_temperature(self, agent_name: str) -> float:
        """Get appropriate temperature for agent type"""
        temperatures = {
            'system_agent': 0.1,           # Very deterministic
            'software_install_agent': 0.2,  # Mostly deterministic
            'shell_assistant_agent': 0.3,   # Some creativity
            'file_management_agent': 0.4,   # More creative organization
            'activity_tracker_agent': 0.1   # Deterministic analysis
        }
        return temperatures.get(agent_name, 0.3)
    
    def _get_recommended_models(self, level: str) -> List[str]:
        """Get list of recommended models to download"""
        capability = self.llm_capabilities.get(level)
        return capability.models if capability else ['rule-based']
    
    def _calculate_parallel_capacity(self, hw_info: HardwareInfo) -> int:
        """Calculate how many agents can run in parallel"""
        # Conservative calculation based on RAM
        ram_per_agent_gb = 2.0  # Estimate
        max_parallel = int(hw_info.ram_available_gb / ram_per_agent_gb)
        
        # Consider CPU cores
        cpu_limit = max(1, hw_info.cpu_logical_count // 2)
        
        return min(max_parallel, cpu_limit, 5)  # Max 5 agents
    
    def _estimate_performance(self, level: str, hw_info: HardwareInfo) -> Dict:
        """Estimate system performance characteristics"""
        performance_multipliers = {
            'HIGH': 1.0,
            'MEDIUM': 0.7,
            'LOW': 0.4,
            'FALLBACK': 0.1
        }
        
        base_performance = performance_multipliers.get(level, 0.5)
        
        # Adjust for hardware
        if hw_info.gpus:
            base_performance *= 1.5  # GPU acceleration
        
        if hw_info.cpu_count >= 8:
            base_performance *= 1.2  # Multi-core boost
        
        return {
            'response_time_estimate_ms': int(1000 / base_performance),
            'throughput_multiplier': base_performance,
            'quality_score': base_performance,
            'can_handle_complex_tasks': level in ['HIGH', 'MEDIUM']
        }
    
    async def download_recommended_models(self, llm_config: Dict) -> Dict:
        """Download recommended LLM models"""
        if not OLLAMA_AVAILABLE:
            self.logger.warning("Ollama not available, skipping model downloads")
            return {'success': False, 'error': 'Ollama not available'}
        
        download_results = {}
        recommended_models = llm_config.get('recommended_models', [])
        
        for model in recommended_models:
            if model == 'rule-based':
                continue
                
            try:
                self.logger.info(f"Downloading model: {model}")
                
                # Check if model already exists
                try:
                    ollama.show(model)
                    download_results[model] = {'success': True, 'already_exists': True}
                    continue
                except:
                    pass
                
                # Download model
                result = ollama.pull(model)
                download_results[model] = {'success': True, 'downloaded': True}
                self.logger.info(f"Successfully downloaded {model}")
                
            except Exception as e:
                download_results[model] = {'success': False, 'error': str(e)}
                self.logger.error(f"Failed to download {model}: {e}")
        
        return {
            'success': True,
            'results': download_results,
            'total_models': len(recommended_models),
            'successful_downloads': len([r for r in download_results.values() if r['success']])
        }
    
    def save_hardware_profile(self, scan_result: Dict, profile_path: Optional[str] = None):
        """Save hardware profile for future reference"""
        if not profile_path:
            profile_path = Path.home() / ".ai_hardware_profile.json"
        
        try:
            with open(profile_path, 'w') as f:
                json.dump(scan_result, f, indent=2)
            self.logger.info(f"Hardware profile saved to {profile_path}")
        except Exception as e:
            self.logger.error(f"Failed to save hardware profile: {e}")
    
    def load_hardware_profile(self, profile_path: Optional[str] = None) -> Optional[Dict]:
        """Load cached hardware profile"""
        if not profile_path:
            profile_path = Path.home() / ".ai_hardware_profile.json"
        
        try:
            if Path(profile_path).exists():
                with open(profile_path, 'r') as f:
                    profile = json.load(f)
                
                # Check if profile is recent (within 24 hours)
                if time.time() - profile.get('scan_timestamp', 0) < 86400:
                    self.logger.info("Using cached hardware profile")
                    return profile
                else:
                    self.logger.info("Hardware profile is stale, will rescan")
            
        except Exception as e:
            self.logger.error(f"Failed to load hardware profile: {e}")
        
        return None


# Testing interface
async def main():
    scanner = HardwareScanner()
    
    print("🔍 Starting hardware scan...")
    scan_result = await scanner.scan_system()
    
    print("\n" + "="*60)
    print("HARDWARE SCAN RESULTS")
    print("="*60)
    
    hw = scan_result['hardware']
    print(f"CPU: {hw['cpu']['model']} ({hw['cpu']['count']} cores)")
    print(f"RAM: {hw['memory']['total_gb']:.1f} GB total, {hw['memory']['available_gb']:.1f} GB available")
    print(f"GPUs: {len(hw['gpus'])} detected")
    for i, gpu in enumerate(hw['gpus']):
        print(f"  GPU {i}: {gpu['name']} ({gpu['memory_total_mb']} MB)")
    print(f"Storage: {hw['storage']['free_gb']:.1f} GB free of {hw['storage']['total_gb']:.1f} GB")
    print(f"Network: {'Connected' if hw['network']['connected'] else 'Disconnected'}")
    print(f"OS: {hw['os']['system']} {hw['os']['release']}")
    
    print("\n" + "="*60)
    print("LLM CONFIGURATION")
    print("="*60)
    
    llm_config = scan_result['llm_config']
    print(f"Overall Capability: {llm_config['overall_level']}")
    print(f"GPU Acceleration: {'Yes' if llm_config['gpu_acceleration'] else 'No'}")
    print(f"Parallel Agents: {llm_config['parallel_agents']}")
    print(f"Recommended Models: {', '.join(llm_config['recommended_models'])}")
    
    print("\nAgent Configurations:")
    for agent, config in llm_config['agent_configs'].items():
        print(f"  {agent}: {config['model']} (level: {config['level']})")
    
    print("\nPerformance Estimates:")
    perf = llm_config['estimated_performance']
    print(f"  Response Time: ~{perf['response_time_estimate_ms']} ms")
    print(f"  Quality Score: {perf['quality_score']:.2f}")
    print(f"  Complex Tasks: {'Yes' if perf['can_handle_complex_tasks'] else 'No'}")
    
    # Save profile
    scanner.save_hardware_profile(scan_result)
    
    print("\n🎯 Hardware scan complete!")


if __name__ == "__main__":
    asyncio.run(main())