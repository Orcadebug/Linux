# AI-Native Linux OS - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI-Native Linux OS                           │
├─────────────────────────────────────────────────────────────────┤
│                     User Interface Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  AI Shell Assistant  │  Quest Log CLI  │  System Commands      │
├─────────────────────────────────────────────────────────────────┤
│                      AI Services Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Quest Log Daemon   │  Kernel Monitor  │  Self-Healing Service │
├─────────────────────────────────────────────────────────────────┤
│                     System Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  Linux Kernel  │  SystemD  │  Python Runtime  │  SQLite        │
├─────────────────────────────────────────────────────────────────┤
│                   Hardware Layer                                │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. AI Shell Assistant (`src/ai_shell/`)

**Purpose**: Natural language to shell command translation with safety checks.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│             AI Shell Assistant              │
├─────────────────────────────────────────────┤
│  Natural Language Parser                    │
│  ├─ Rule-based Translation Engine           │
│  ├─ Context Analyzer                        │
│  └─ Safety Checker                          │
├─────────────────────────────────────────────┤
│  Command Executor                           │
│  ├─ Subprocess Manager                      │
│  ├─ Output Formatter                        │
│  └─ History Manager                         │
├─────────────────────────────────────────────┤
│  Configuration Manager                      │
│  └─ JSON Config Loader                      │
└─────────────────────────────────────────────┘
```

**Key Components**:
- **AIShellAssistant**: Main class handling translation and execution
- **Translation Engine**: Rule-based natural language processing
- **Safety Checker**: Prevents dangerous command execution
- **History Manager**: Tracks command history and success rates

**Data Flow**:
1. User input → Natural Language Parser
2. Parser → Translation Engine
3. Translation Engine → Safety Checker
4. Safety Checker → Command Executor
5. Executor → Output Formatter → User

### 2. Quest Log System (`src/quest_log/`)

**Purpose**: Comprehensive system activity logging and analysis.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│              Quest Log System               │
├─────────────────────────────────────────────┤
│  Quest Log Daemon                           │
│  ├─ Bash History Monitor                    │
│  ├─ System Event Monitor                    │
│  ├─ SQLite Database Manager                 │
│  └─ Event Logger                            │
├─────────────────────────────────────────────┤
│  Quest Log CLI                              │
│  ├─ Query Engine                            │
│  ├─ Data Formatter                          │
│  ├─ Search Engine                           │
│  └─ Statistics Generator                    │
├─────────────────────────────────────────────┤
│  Database Schema                            │
│  ├─ Events Table                            │
│  └─ Commands Table                          │
└─────────────────────────────────────────────┘
```

**Database Schema**:
```sql
-- Events Table
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    data TEXT,
    metadata TEXT
);

-- Commands Table  
CREATE TABLE commands (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user TEXT NOT NULL,
    command TEXT NOT NULL,
    working_directory TEXT,
    exit_code INTEGER,
    output TEXT,
    duration REAL
);
```

**Key Components**:
- **QuestLogDaemon**: Background service for continuous monitoring
- **QuestLogCLI**: Command-line interface for data retrieval
- **Database Manager**: SQLite operations and schema management
- **Event Monitors**: Various system activity watchers

### 3. AI Kernel Monitor (`src/kernel_monitor/`)

**Purpose**: Intelligent system monitoring with anomaly detection.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│             AI Kernel Monitor               │
├─────────────────────────────────────────────┤
│  Metrics Collection Layer                   │
│  ├─ CPU Monitor                             │
│  ├─ Memory Monitor                          │
│  ├─ Disk Monitor                            │
│  ├─ Network Monitor                         │
│  └─ Process Monitor                         │
├─────────────────────────────────────────────┤
│  Analysis Layer                             │
│  ├─ Threshold Checker                       │
│  ├─ Anomaly Detector (ML)                   │
│  ├─ Trend Analyzer                          │
│  └─ Alert Generator                         │
├─────────────────────────────────────────────┤
│  Response Layer                             │
│  ├─ Suggestion Engine                       │
│  ├─ Alert Manager                           │
│  └─ Quest Log Integration                   │
└─────────────────────────────────────────────┘
```

**Machine Learning Pipeline**:
1. **Data Collection**: Continuous system metrics gathering
2. **Feature Engineering**: Transform raw metrics into ML features
3. **Training**: Use Isolation Forest for anomaly detection
4. **Prediction**: Real-time anomaly scoring
5. **Action**: Generate alerts and suggestions

**Key Components**:
- **AIKernelMonitor**: Main monitoring orchestrator
- **MetricsCollector**: System metrics gathering using psutil
- **AnomalyDetector**: ML-based anomaly detection
- **AlertManager**: Intelligent alerting with cooldown
- **SuggestionEngine**: Contextual problem-solving advice

### 4. Self-Healing Service (`src/self_healing/`)

**Purpose**: Automatic service recovery and system maintenance.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│            Self-Healing Service             │
├─────────────────────────────────────────────┤
│  Service Monitor                            │
│  ├─ SystemD Service Checker                 │
│  ├─ Process Monitor                         │
│  ├─ Health Check Engine                     │
│  └─ Dependency Tracker                      │
├─────────────────────────────────────────────┤
│  Recovery Engine                            │
│  ├─ Restart Manager                         │
│  ├─ Failure Analysis                        │
│  ├─ Recovery Strategy Selector              │
│  └─ Escalation Manager                      │
├─────────────────────────────────────────────┤
│  Policy Engine                              │
│  ├─ Restart Policy Manager                  │
│  ├─ Cooldown Manager                        │
│  ├─ Priority Manager                        │
│  └─ Configuration Manager                   │
└─────────────────────────────────────────────┘
```

**Recovery Workflow**:
1. **Detection**: Continuous service/process monitoring
2. **Analysis**: Determine failure type and cause
3. **Strategy**: Select appropriate recovery action
4. **Execution**: Perform restart/recovery with policies
5. **Verification**: Confirm successful recovery
6. **Logging**: Record all actions for audit

**Key Components**:
- **SelfHealingService**: Main orchestrator
- **ServiceMonitor**: SystemD service health checking
- **ProcessMonitor**: Custom process monitoring
- **RecoveryEngine**: Smart restart logic with policies
- **PolicyManager**: Configurable recovery strategies

## Integration Architecture

### Inter-Component Communication

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  AI Shell       │    │  Quest Log      │    │  Kernel Monitor │
│  Assistant      │    │  System         │    │                 │
│                 │    │                 │    │                 │
│  ┌─────────────┐│    │  ┌─────────────┐│    │  ┌─────────────┐│
│  │   History   ││────┼─→│  Command    ││    │  │   Metrics   ││
│  │   Logger    ││    │  │   Logger    ││    │  │ Collection  ││
│  └─────────────┘│    │  └─────────────┘│    │  └─────────────┘│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  SQLite DB      │    │  SQLite DB      │    │  JSON Logs      │
│  (History)      │    │  (Events/Cmds)  │    │  (Alerts)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                │
                                ▼
                    ┌─────────────────┐
                    │  Self-Healing   │
                    │  Service        │
                    │                 │
                    │  ┌─────────────┐│
                    │  │   Action    ││
                    │  │   Logger    ││
                    │  └─────────────┘│
                    └─────────────────┘
```

### Data Flow Architecture

1. **User Interaction**: 
   - User → AI Shell Assistant → Command Execution
   - Command → Quest Log Daemon → Database

2. **System Monitoring**:
   - System → Kernel Monitor → Analysis → Alerts
   - Alerts → Quest Log System → Historical Data

3. **Service Management**:
   - Self-Healing Service → Service Checks → Recovery Actions
   - Recovery Actions → Quest Log System → Audit Trail

4. **Data Storage**:
   - SQLite databases for structured data
   - JSON logs for configuration and alerts
   - System logs via journalctl

## Security Architecture

### Security Layers

1. **Input Validation**:
   - AI Shell Assistant validates and sanitizes all user input
   - Dangerous command detection and blocking
   - Parameter injection prevention

2. **Privilege Separation**:
   - Quest Log Daemon runs as unprivileged user
   - Kernel Monitor runs as unprivileged user
   - Self-Healing Service runs as root (minimal privileges)

3. **Data Protection**:
   - Database files with restricted permissions
   - Configuration files owned by root
   - Sensitive data exclusion from logs

4. **Service Isolation**:
   - Each service runs in separate process
   - SystemD service isolation
   - Resource limitations via systemd

### Security Controls

- **Command Safety**: Dangerous command detection and user confirmation
- **File Permissions**: Strict file system permissions
- **Process Isolation**: Service separation and resource limits
- **Audit Logging**: Comprehensive activity logging
- **Configuration Validation**: Input sanitization and validation

## Performance Architecture

### Performance Characteristics

1. **AI Shell Assistant**:
   - Response time: <100ms for translation
   - Memory usage: <50MB
   - CPU usage: <5% during operation

2. **Quest Log System**:
   - Database writes: <1ms per event
   - Query performance: <100ms for complex queries
   - Storage: ~1MB per 1000 events

3. **Kernel Monitor**:
   - Monitoring interval: 5 seconds (configurable)
   - Memory usage: <100MB
   - CPU usage: <2% continuous

4. **Self-Healing Service**:
   - Check interval: 30 seconds (configurable)
   - Recovery time: <10 seconds
   - Memory usage: <20MB

### Optimization Strategies

1. **Database Optimization**:
   - Indexed queries for fast lookups
   - Periodic database cleanup
   - Efficient data structures

2. **Memory Management**:
   - Circular buffers for historical data
   - Configurable history limits
   - Garbage collection optimization

3. **CPU Optimization**:
   - Efficient polling intervals
   - Async I/O where possible
   - Smart caching strategies

4. **Storage Optimization**:
   - Compressed data storage
   - Log rotation policies
   - Efficient file formats

## Deployment Architecture

### Installation Methods

1. **ISO Installation**:
   - Base Ubuntu system + AI components
   - Pre-configured services
   - Automated setup scripts

2. **Package Installation**:
   - Install on existing Linux systems
   - SystemD service integration
   - Configuration management

3. **Container Deployment**:
   - Docker containers for each service
   - Orchestration with docker-compose
   - Volume management for data

### Configuration Management

- **System Configuration**: `/etc/ai-native-linux/`
- **Service Configuration**: SystemD service files
- **User Configuration**: Home directory dotfiles
- **Runtime Configuration**: Environment variables

---

This architecture provides a solid foundation for the AI-Native Linux OS MVP while maintaining modularity, security, and performance.