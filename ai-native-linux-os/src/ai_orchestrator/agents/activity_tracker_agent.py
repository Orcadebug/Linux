#!/usr/bin/env python3
"""
Activity Tracker Agent - User pattern learning, workflow analysis, and productivity insights
"""

import asyncio
import json
import os
import sqlite3
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from statistics import mean, median

from .base_agent import BaseAgent, AgentMessage, MessageType, AgentState


class ActivityPattern:
    """Data structure for activity patterns"""
    
    def __init__(self, pattern_type: str, description: str, frequency: int, confidence: float):
        self.pattern_type = pattern_type  # daily, weekly, project, workflow
        self.description = description
        self.frequency = frequency
        self.confidence = confidence  # 0.0 to 1.0
        self.discovered_at = datetime.now()
        self.last_seen = datetime.now()


class WorkflowSuggestion:
    """Data structure for workflow suggestions"""
    
    def __init__(self, suggestion_type: str, title: str, description: str, commands: List[str] = None):
        self.suggestion_type = suggestion_type  # optimization, automation, learning
        self.title = title
        self.description = description
        self.commands = commands or []
        self.potential_time_saved = 0  # minutes
        self.priority = "medium"  # low, medium, high
        self.created_at = datetime.now()


class ActivityTrackerAgent(BaseAgent):
    """Agent for tracking user activity and learning patterns"""
    
    def __init__(self, agent_id: str, security_manager, config: Dict):
        super().__init__(agent_id, security_manager, config)
        self.name = "Activity Tracker Agent"
        self.description = "Learns user patterns and suggests workflow optimizations"
        
        # Database configuration
        self.db_path = config.get('db_path', Path.home() / ".ai_activity_tracker.db")
        
        # Tracking configuration
        self.tracking_config = {
            "command_history_days": config.get('command_history_days', 30),
            "pattern_analysis_interval": config.get('pattern_analysis_interval', 3600),  # 1 hour
            "min_pattern_frequency": config.get('min_pattern_frequency', 3),
            "productivity_analysis_enabled": config.get('productivity_analysis', True),
            "workflow_suggestions_enabled": config.get('workflow_suggestions', True),
            "privacy_mode": config.get('privacy_mode', False)  # Anonymize sensitive data
        }
        
        # Activity tracking state
        self.discovered_patterns = []
        self.workflow_suggestions = []
        self.productivity_metrics = {}
        self.tracking_active = False
        self.analysis_task = None
        
        # Pattern analysis
        self.command_clusters = {}
        self.time_patterns = {}
        self.project_workflows = {}
        
        # Initialize database
        self._setup_database()
        
        self.logger.info("Activity Tracker Agent initialized")
    
    def _setup_database(self):
        """Initialize SQLite database for activity tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    data TEXT,
                    metadata TEXT,
                    user_id TEXT,
                    session_id TEXT
                )
            ''')
            
            # Commands table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user TEXT NOT NULL,
                    command TEXT NOT NULL,
                    working_directory TEXT,
                    exit_code INTEGER,
                    output TEXT,
                    duration REAL,
                    command_category TEXT,
                    project_context TEXT
                )
            ''')
            
            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_time DATETIME,
                    total_commands INTEGER DEFAULT 0,
                    total_duration REAL DEFAULT 0,
                    primary_activity TEXT,
                    productivity_score REAL
                )
            ''')
            
            # Patterns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    frequency INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    pattern_data TEXT
                )
            ''')
            
            # Productivity metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS productivity_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    commands_count INTEGER,
                    unique_commands INTEGER,
                    session_duration REAL,
                    error_rate REAL,
                    productivity_score REAL,
                    primary_activities TEXT,
                    insights TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Activity tracking database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to setup database: {e}")
    
    async def start_tracking(self):
        """Start activity tracking"""
        if self.tracking_active:
            return {"status": "already_running"}
        
        self.tracking_active = True
        self.analysis_task = asyncio.create_task(self._analysis_loop())
        
        self.logger.info("Activity tracking started")
        return {"status": "started", "analysis_interval": self.tracking_config["pattern_analysis_interval"]}
    
    async def stop_tracking(self):
        """Stop activity tracking"""
        if not self.tracking_active:
            return {"status": "already_stopped"}
        
        self.tracking_active = False
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Activity tracking stopped")
        return {"status": "stopped"}
    
    async def process_message(self, message: AgentMessage) -> Optional[Dict]:
        """Process activity tracking requests"""
        try:
            if message.type == MessageType.TASK:
                return await self._handle_tracking_task(message.content)
            elif message.type == MessageType.QUERY:
                return await self._handle_tracking_query(message.content)
            else:
                return await super().process_message(message)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def _handle_tracking_task(self, content: Dict) -> Dict:
        """Handle activity tracking tasks"""
        task_type = content.get('type', 'start_tracking')
        
        if task_type == 'start_tracking':
            return await self.start_tracking()
        
        elif task_type == 'stop_tracking':
            return await self.stop_tracking()
        
        elif task_type == 'log_command':
            command_data = content.get('command_data', {})
            return await self._log_command(command_data)
        
        elif task_type == 'log_event':
            event_data = content.get('event_data', {})
            return await self._log_event(event_data)
        
        elif task_type == 'analyze_patterns':
            return await self._analyze_user_patterns()
        
        elif task_type == 'generate_insights':
            days = content.get('days', 7)
            return await self._generate_productivity_insights(days)
        
        elif task_type == 'suggest_workflows':
            return await self._generate_workflow_suggestions()
        
        else:
            return {"error": f"Unknown task type: {task_type}", "status": "failed"}
    
    async def _handle_tracking_query(self, content: Dict) -> Dict:
        """Handle queries about activity and patterns"""
        query_type = content.get('type', 'activity_summary')
        
        if query_type == 'activity_summary':
            days = content.get('days', 7)
            return await self._get_activity_summary(days)
        
        elif query_type == 'patterns':
            pattern_type = content.get('pattern_type', 'all')
            return await self._get_discovered_patterns(pattern_type)
        
        elif query_type == 'productivity':
            days = content.get('days', 30)
            return await self._get_productivity_analysis(days)
        
        elif query_type == 'workflow_suggestions':
            return await self._get_workflow_suggestions()
        
        elif query_type == 'command_stats':
            days = content.get('days', 7)
            return await self._get_command_statistics(days)
        
        elif query_type == 'project_analysis':
            project = content.get('project', None)
            return await self._get_project_analysis(project)
        
        else:
            return {"error": f"Unknown query type: {query_type}", "status": "failed"}
    
    async def _analysis_loop(self):
        """Main analysis loop for pattern discovery"""
        try:
            while self.tracking_active:
                # Perform pattern analysis
                await self._analyze_user_patterns()
                
                # Generate productivity insights
                await self._generate_productivity_insights(1)  # Daily analysis
                
                # Update workflow suggestions
                await self._generate_workflow_suggestions()
                
                # Wait for next analysis cycle
                await asyncio.sleep(self.tracking_config["pattern_analysis_interval"])
                
        except asyncio.CancelledError:
            self.logger.info("Analysis loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in analysis loop: {e}")
            self.tracking_active = False
    
    async def _log_command(self, command_data: Dict) -> Dict:
        """Log a shell command execution"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract command data
            user = command_data.get('user', os.getenv('USER', 'unknown'))
            command = command_data.get('command', '')
            working_directory = command_data.get('working_directory', os.getcwd())
            exit_code = command_data.get('exit_code', 0)
            output = command_data.get('output', '')
            duration = command_data.get('duration', 0.0)
            
            # Categorize command
            command_category = self._categorize_command(command)
            project_context = self._detect_project_context(working_directory, command)
            
            # Privacy mode: anonymize sensitive data
            if self.tracking_config['privacy_mode']:
                command = self._anonymize_command(command)
                output = self._anonymize_output(output)
                working_directory = self._anonymize_path(working_directory)
            
            cursor.execute('''
                INSERT INTO commands (user, command, working_directory, exit_code, output, duration, command_category, project_context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user, command, working_directory, exit_code, output, duration, command_category, project_context))
            
            conn.commit()
            conn.close()
            
            return {"status": "logged", "category": command_category, "project": project_context}
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _log_event(self, event_data: Dict) -> Dict:
        """Log a system event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            event_type = event_data.get('type', 'unknown')
            source = event_data.get('source', 'system')
            data = event_data.get('data', {})
            metadata = event_data.get('metadata', {})
            user_id = event_data.get('user_id', os.getenv('USER', 'unknown'))
            session_id = event_data.get('session_id', 'default')
            
            cursor.execute('''
                INSERT INTO events (event_type, source, data, metadata, user_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (event_type, source, json.dumps(data), json.dumps(metadata), user_id, session_id))
            
            conn.commit()
            conn.close()
            
            return {"status": "logged"}
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _categorize_command(self, command: str) -> str:
        """Categorize command by type"""
        command_lower = command.lower()
        
        # Development commands
        if any(word in command_lower for word in ['git', 'python', 'pip', 'npm', 'node', 'java', 'gcc', 'make']):
            return 'development'
        
        # File operations
        elif any(word in command_lower for word in ['ls', 'cd', 'cp', 'mv', 'rm', 'mkdir', 'find', 'grep']):
            return 'file_operations'
        
        # System administration
        elif any(word in command_lower for word in ['sudo', 'apt', 'yum', 'systemctl', 'service', 'crontab']):
            return 'system_admin'
        
        # Network operations
        elif any(word in command_lower for word in ['wget', 'curl', 'ssh', 'scp', 'ping', 'netstat']):
            return 'network'
        
        # AI/ML operations
        elif any(word in command_lower for word in ['nvidia-smi', 'jupyter', 'tensorboard', 'conda']):
            return 'ai_ml'
        
        # Text processing
        elif any(word in command_lower for word in ['sed', 'awk', 'sort', 'uniq', 'head', 'tail', 'cat']):
            return 'text_processing'
        
        # Media operations
        elif any(word in command_lower for word in ['ffmpeg', 'convert', 'gimp', 'vlc']):
            return 'media'
        
        else:
            return 'other'
    
    def _detect_project_context(self, working_directory: str, command: str) -> str:
        """Detect project context from directory and command"""
        path = Path(working_directory)
        
        # Check for common project indicators
        project_indicators = {
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml', '__pycache__'],
            'nodejs': ['package.json', 'node_modules', 'yarn.lock'],
            'web': ['index.html', 'style.css', 'script.js'],
            'docker': ['Dockerfile', 'docker-compose.yml'],
            'ai_ml': ['train.py', 'model.py', 'data/', 'models/'],
            'git': ['.git'],
            'docs': ['README.md', 'docs/', '*.md']
        }
        
        for project_type, indicators in project_indicators.items():
            for indicator in indicators:
                if '*' in indicator:
                    # Pattern matching
                    pattern = indicator.replace('*', '.*')
                    if any(re.match(pattern, f.name) for f in path.rglob('*') if f.is_file()):
                        return project_type
                else:
                    # Direct file/directory check
                    if (path / indicator).exists():
                        return project_type
        
        # Check command for project hints
        command_lower = command.lower()
        if any(word in command_lower for word in ['python', 'pip']):
            return 'python'
        elif any(word in command_lower for word in ['npm', 'node', 'yarn']):
            return 'nodejs'
        elif any(word in command_lower for word in ['git']):
            return 'git'
        
        return 'general'
    
    def _anonymize_command(self, command: str) -> str:
        """Anonymize sensitive information in commands"""
        # Replace file paths with placeholders
        command = re.sub(r'/home/[^/\s]+', '/home/USER', command)
        command = re.sub(r'/Users/[^/\s]+', '/Users/USER', command)
        
        # Replace IP addresses
        command = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP_ADDRESS', command)
        
        # Replace URLs
        command = re.sub(r'https?://[^\s]+', 'URL', command)
        
        # Replace email addresses
        command = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL', command)
        
        return command
    
    def _anonymize_output(self, output: str) -> str:
        """Anonymize sensitive information in command output"""
        if len(output) > 1000:  # Truncate long outputs
            output = output[:1000] + "... [truncated]"
        
        return self._anonymize_command(output)  # Apply same anonymization rules
    
    def _anonymize_path(self, path: str) -> str:
        """Anonymize file paths"""
        return self._anonymize_command(path)
    
    async def _analyze_user_patterns(self) -> Dict:
        """Analyze user command patterns and discover habits"""
        try:
            patterns_found = []
            
            # Analyze temporal patterns
            temporal_patterns = await self._analyze_temporal_patterns()
            patterns_found.extend(temporal_patterns)
            
            # Analyze command sequences
            sequence_patterns = await self._analyze_command_sequences()
            patterns_found.extend(sequence_patterns)
            
            # Analyze project workflows
            workflow_patterns = await self._analyze_project_workflows()
            patterns_found.extend(workflow_patterns)
            
            # Store discovered patterns
            await self._store_patterns(patterns_found)
            
            return {
                "status": "completed",
                "patterns_found": len(patterns_found),
                "patterns": [
                    {
                        "type": p.pattern_type,
                        "description": p.description,
                        "frequency": p.frequency,
                        "confidence": p.confidence
                    }
                    for p in patterns_found
                ]
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _analyze_temporal_patterns(self) -> List[ActivityPattern]:
        """Analyze when user is most active"""
        patterns = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Analyze hourly patterns
            cursor.execute('''
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM commands
                WHERE timestamp > datetime('now', '-30 days')
                GROUP BY hour
                ORDER BY count DESC
            ''')
            
            hourly_data = cursor.fetchall()
            if hourly_data:
                peak_hour, peak_count = hourly_data[0]
                if peak_count >= self.tracking_config['min_pattern_frequency']:
                    patterns.append(ActivityPattern(
                        "temporal",
                        f"Most active during hour {peak_hour}:00-{int(peak_hour)+1}:00 ({peak_count} commands)",
                        peak_count,
                        0.8
                    ))
            
            # Analyze daily patterns
            cursor.execute('''
                SELECT strftime('%w', timestamp) as day_of_week, COUNT(*) as count
                FROM commands
                WHERE timestamp > datetime('now', '-30 days')
                GROUP BY day_of_week
                ORDER BY count DESC
            ''')
            
            daily_data = cursor.fetchall()
            if daily_data:
                day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                peak_day, peak_count = daily_data[0]
                if peak_count >= self.tracking_config['min_pattern_frequency'] * 4:  # Weekly pattern
                    patterns.append(ActivityPattern(
                        "temporal",
                        f"Most active on {day_names[int(peak_day)]} ({peak_count} commands)",
                        peak_count,
                        0.7
                    ))
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error analyzing temporal patterns: {e}")
        
        return patterns
    
    async def _analyze_command_sequences(self) -> List[ActivityPattern]:
        """Analyze common command sequences"""
        patterns = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent command sequences
            cursor.execute('''
                SELECT command, timestamp
                FROM commands
                WHERE timestamp > datetime('now', '-7 days')
                ORDER BY timestamp
            ''')
            
            commands = cursor.fetchall()
            
            if len(commands) < 3:
                return patterns
            
            # Find common 2-command sequences
            sequences = defaultdict(int)
            for i in range(len(commands) - 1):
                cmd1 = commands[i][0].split()[0] if commands[i][0] else ''  # Get base command
                cmd2 = commands[i+1][0].split()[0] if commands[i+1][0] else ''
                
                if cmd1 and cmd2:
                    sequences[(cmd1, cmd2)] += 1
            
            # Find most common sequences
            for (cmd1, cmd2), count in sequences.items():
                if count >= self.tracking_config['min_pattern_frequency']:
                    patterns.append(ActivityPattern(
                        "workflow",
                        f"Often runs '{cmd1}' followed by '{cmd2}' ({count} times)",
                        count,
                        min(0.9, count / 10)  # Higher confidence with more occurrences
                    ))
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error analyzing command sequences: {e}")
        
        return patterns
    
    async def _analyze_project_workflows(self) -> List[ActivityPattern]:
        """Analyze project-specific workflow patterns"""
        patterns = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Analyze command patterns by project context
            cursor.execute('''
                SELECT project_context, command_category, COUNT(*) as count
                FROM commands
                WHERE timestamp > datetime('now', '-14 days')
                AND project_context != 'general'
                GROUP BY project_context, command_category
                HAVING count >= ?
                ORDER BY project_context, count DESC
            ''', (self.tracking_config['min_pattern_frequency'],))
            
            project_patterns = cursor.fetchall()
            
            for project, category, count in project_patterns:
                patterns.append(ActivityPattern(
                    "project",
                    f"In {project} projects, frequently uses {category} commands ({count} times)",
                    count,
                    0.6
                ))
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error analyzing project workflows: {e}")
        
        return patterns
    
    async def _store_patterns(self, patterns: List[ActivityPattern]):
        """Store discovered patterns in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for pattern in patterns:
                # Check if similar pattern exists
                cursor.execute('''
                    SELECT id FROM patterns
                    WHERE pattern_type = ? AND description = ?
                ''', (pattern.pattern_type, pattern.description))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing pattern
                    cursor.execute('''
                        UPDATE patterns
                        SET frequency = ?, confidence = ?, last_seen = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (pattern.frequency, pattern.confidence, existing[0]))
                else:
                    # Insert new pattern
                    cursor.execute('''
                        INSERT INTO patterns (pattern_type, description, frequency, confidence, pattern_data)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (pattern.pattern_type, pattern.description, pattern.frequency, 
                          pattern.confidence, json.dumps({})))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing patterns: {e}")
    
    async def _generate_productivity_insights(self, days: int) -> Dict:
        """Generate productivity insights for specified period"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get command statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_commands,
                    COUNT(DISTINCT command) as unique_commands,
                    AVG(duration) as avg_duration,
                    SUM(CASE WHEN exit_code != 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as error_rate,
                    GROUP_CONCAT(DISTINCT command_category) as categories
                FROM commands
                WHERE timestamp > datetime('now', '-{} days')
            '''.format(days))
            
            stats = cursor.fetchone()
            
            if not stats or stats[0] == 0:
                return {"status": "no_data", "message": "No activity data available"}
            
            total_commands, unique_commands, avg_duration, error_rate, categories = stats
            categories_list = categories.split(',') if categories else []
            
            # Calculate productivity score (0-100)
            productivity_score = self._calculate_productivity_score(
                total_commands, unique_commands, error_rate, categories_list
            )
            
            # Get most used commands
            cursor.execute('''
                SELECT command, COUNT(*) as count
                FROM commands
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY command
                ORDER BY count DESC
                LIMIT 10
            '''.format(days))
            
            top_commands = cursor.fetchall()
            
            # Generate insights
            insights = self._generate_insights_text(
                productivity_score, total_commands, unique_commands, 
                error_rate, categories_list, top_commands
            )
            
            # Store daily productivity metrics
            if days == 1:  # Daily metrics
                cursor.execute('''
                    INSERT OR REPLACE INTO productivity_metrics 
                    (date, commands_count, unique_commands, error_rate, productivity_score, primary_activities, insights)
                    VALUES (date('now'), ?, ?, ?, ?, ?, ?)
                ''', (total_commands, unique_commands, error_rate, productivity_score, 
                      ','.join(categories_list), json.dumps(insights)))
            
            conn.commit()
            conn.close()
            
            return {
                "status": "completed",
                "period_days": days,
                "productivity_score": productivity_score,
                "total_commands": total_commands,
                "unique_commands": unique_commands,
                "error_rate": error_rate * 100,  # Convert to percentage
                "avg_duration": avg_duration or 0,
                "primary_activities": categories_list,
                "top_commands": [{"command": cmd, "count": count} for cmd, count in top_commands],
                "insights": insights
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _calculate_productivity_score(self, total_commands: int, unique_commands: int, 
                                    error_rate: float, categories: List[str]) -> float:
        """Calculate productivity score based on activity metrics"""
        score = 50  # Base score
        
        # Command diversity bonus
        if total_commands > 0:
            diversity_ratio = unique_commands / total_commands
            score += diversity_ratio * 20  # Up to 20 points for diversity
        
        # Error rate penalty
        score -= error_rate * 30  # Up to 30 points penalty for high error rate
        
        # Activity category bonus
        productive_categories = ['development', 'ai_ml', 'text_processing']
        productive_count = sum(1 for cat in categories if cat in productive_categories)
        score += productive_count * 5  # 5 points per productive category
        
        # Activity volume bonus
        if total_commands > 50:
            score += 10
        elif total_commands > 20:
            score += 5
        
        return max(0, min(100, score))  # Clamp between 0-100
    
    def _generate_insights_text(self, productivity_score: float, total_commands: int,
                              unique_commands: int, error_rate: float, categories: List[str],
                              top_commands: List[Tuple]) -> List[str]:
        """Generate human-readable insights"""
        insights = []
        
        # Productivity assessment
        if productivity_score >= 80:
            insights.append("Excellent productivity! You're using diverse commands with low error rates.")
        elif productivity_score >= 60:
            insights.append("Good productivity with room for improvement.")
        elif productivity_score >= 40:
            insights.append("Moderate productivity. Consider learning more efficient workflows.")
        else:
            insights.append("Low productivity detected. Focus on reducing errors and expanding command knowledge.")
        
        # Error rate insights
        if error_rate > 0.2:
            insights.append("High error rate detected. Consider double-checking commands before execution.")
        elif error_rate > 0.1:
            insights.append("Moderate error rate. Review failed commands to improve accuracy.")
        elif error_rate < 0.05:
            insights.append("Excellent command accuracy! Very low error rate.")
        
        # Command diversity insights
        if total_commands > 0:
            diversity = unique_commands / total_commands
            if diversity > 0.7:
                insights.append("Great command diversity! You're using many different tools.")
            elif diversity < 0.3:
                insights.append("Consider exploring more command variety to improve efficiency.")
        
        # Activity focus insights
        if 'development' in categories:
            insights.append("Strong focus on development activities.")
        if 'ai_ml' in categories:
            insights.append("Active in AI/ML workflows.")
        if 'system_admin' in categories:
            insights.append("Significant system administration work.")
        
        # Top command insights
        if top_commands:
            most_used = top_commands[0][0]
            insights.append(f"Most frequently used command: '{most_used}'")
        
        return insights
    
    async def _generate_workflow_suggestions(self) -> Dict:
        """Generate workflow optimization suggestions"""
        try:
            suggestions = []
            
            # Analyze recent command patterns for optimization opportunities
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find repetitive manual tasks
            cursor.execute('''
                SELECT command, COUNT(*) as count, AVG(duration) as avg_duration
                FROM commands
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY command
                HAVING count >= 5
                ORDER BY count DESC
                LIMIT 10
            ''')
            
            repetitive_commands = cursor.fetchall()
            
            for command, count, avg_duration in repetitive_commands:
                if self._is_automatable_command(command):
                    potential_savings = (count * (avg_duration or 0)) / 60  # minutes saved
                    suggestions.append(WorkflowSuggestion(
                        "automation",
                        f"Automate repetitive '{command}' command",
                        f"You've run this command {count} times. Consider creating an alias or script.",
                        [f"alias quick_{len(suggestions)}='{command}'"],
                    ))
                    suggestions[-1].potential_time_saved = potential_savings
                    suggestions[-1].priority = "high" if potential_savings > 10 else "medium"
            
            # Suggest common development workflow optimizations
            if await self._user_works_with_git():
                suggestions.append(WorkflowSuggestion(
                    "optimization",
                    "Git workflow optimization",
                    "Set up git aliases for common operations to save time",
                    [
                        "git config --global alias.st status",
                        "git config --global alias.co checkout",
                        "git config --global alias.br branch",
                        "git config --global alias.cm 'commit -m'"
                    ]
                ))
            
            # Python development suggestions
            if await self._user_works_with_python():
                suggestions.append(WorkflowSuggestion(
                    "optimization",
                    "Python development efficiency",
                    "Use virtual environments and requirements.txt for better project management",
                    [
                        "python3 -m venv venv",
                        "source venv/bin/activate",
                        "pip freeze > requirements.txt"
                    ]
                ))
            
            conn.close()
            
            # Store suggestions
            self.workflow_suggestions = suggestions
            
            return {
                "status": "completed",
                "suggestions_count": len(suggestions),
                "suggestions": [
                    {
                        "type": s.suggestion_type,
                        "title": s.title,
                        "description": s.description,
                        "priority": s.priority,
                        "time_saved_minutes": s.potential_time_saved,
                        "commands": s.commands
                    }
                    for s in suggestions
                ]
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _is_automatable_command(self, command: str) -> bool:
        """Check if a command is suitable for automation"""
        # Commands that are good candidates for aliases or scripts
        automatable_patterns = [
            r'^ls\s+-[la]+',
            r'^git\s+(status|log|diff)',
            r'^docker\s+(ps|images|logs)',
            r'^kubectl\s+get',
            r'^python3?\s+\w+\.py',
            r'^npm\s+(start|test|build)',
        ]
        
        return any(re.match(pattern, command) for pattern in automatable_patterns)
    
    async def _user_works_with_git(self) -> bool:
        """Check if user frequently uses git"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM commands
            WHERE command LIKE 'git %'
            AND timestamp > datetime('now', '-7 days')
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count >= 5
    
    async def _user_works_with_python(self) -> bool:
        """Check if user frequently uses Python"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM commands
            WHERE (command LIKE 'python%' OR command LIKE 'pip%')
            AND timestamp > datetime('now', '-7 days')
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count >= 3
    
    async def _get_activity_summary(self, days: int) -> Dict:
        """Get activity summary for specified period"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_commands,
                    COUNT(DISTINCT DATE(timestamp)) as active_days,
                    MIN(timestamp) as first_activity,
                    MAX(timestamp) as last_activity
                FROM commands
                WHERE timestamp > datetime('now', '-{} days')
            '''.format(days))
            
            basic_stats = cursor.fetchone()
            
            # Category breakdown
            cursor.execute('''
                SELECT command_category, COUNT(*) as count
                FROM commands
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY command_category
                ORDER BY count DESC
            '''.format(days))
            
            category_stats = cursor.fetchall()
            
            # Project activity
            cursor.execute('''
                SELECT project_context, COUNT(*) as count
                FROM commands
                WHERE timestamp > datetime('now', '-{} days')
                AND project_context != 'general'
                GROUP BY project_context
                ORDER BY count DESC
                LIMIT 5
            '''.format(days))
            
            project_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                "status": "success",
                "period_days": days,
                "total_commands": basic_stats[0] if basic_stats else 0,
                "active_days": basic_stats[1] if basic_stats else 0,
                "first_activity": basic_stats[2] if basic_stats else None,
                "last_activity": basic_stats[3] if basic_stats else None,
                "category_breakdown": [{"category": cat, "count": count} for cat, count in category_stats],
                "top_projects": [{"project": proj, "count": count} for proj, count in project_stats]
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def get_status(self) -> Dict:
        """Get agent status"""
        status = await super().get_status()
        status.update({
            'tracking_active': self.tracking_active,
            'patterns_discovered': len(self.discovered_patterns),
            'workflow_suggestions': len(self.workflow_suggestions),
            'database_path': str(self.db_path),
            'privacy_mode': self.tracking_config['privacy_mode']
        })
        return status
    
    async def cleanup(self):
        """Cleanup agent resources"""
        if self.tracking_active:
            await self.stop_tracking()
        await super().cleanup() 