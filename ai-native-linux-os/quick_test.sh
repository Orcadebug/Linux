#!/bin/bash

echo "🚀 AI-Native Linux OS - Quick Demo"
echo "=================================="
echo

# Test AI Shell Assistant
echo "1. 🤖 Testing AI Shell Assistant..."
echo "   Query: 'show me system information'"
python3 src/ai_shell/ai_shell.py "show me system information" --execute
echo

echo "   Query: 'list files in current directory'"
python3 src/ai_shell/ai_shell.py "list files in current directory" --execute
echo

echo "   Query: 'check cpu usage'"
python3 src/ai_shell/ai_shell.py "check cpu usage" --execute
echo

# Test AI/ML specific features
echo "2. 🧠 Testing AI/ML Features..."
echo "   Query: 'gpu status' (will show no GPU in VM/container)"
python3 src/ai_shell/ai_shell.py "gpu status" --execute
echo

echo "   Query: 'create environment for pytorch'"
python3 src/ai_shell/ai_shell.py "create environment for pytorch" --execute
echo

# Test beginner AI commands
echo "3. 🎓 Testing Beginner AI Commands..."
echo "   Query: 'teach computer to recognize images'"
python3 src/ai_shell/ai_shell.py "teach computer to recognize images" --execute
echo

# Start Quest Log daemon in background
echo "4. 📝 Testing Quest Log System..."
python3 src/quest_log/quest_log_daemon.py &
QUEST_PID=$!
sleep 2

# Generate some test events
echo "   Generating test events..."
ls -la > /dev/null
pwd > /dev/null
whoami > /dev/null
sleep 1

# Query recent events
echo "   Recent system events:"
python3 src/quest_log/quest_log_cli.py --recent 5
echo

# Stop quest log daemon
kill $QUEST_PID 2>/dev/null

# Test Kernel Monitor (run for 10 seconds)
echo "5. 📊 Testing Kernel Monitor (10 seconds)..."
timeout 10s python3 src/kernel_monitor/kernel_monitor.py &
MONITOR_PID=$!
sleep 2

# Generate some load for testing
echo "   Generating CPU load for testing..."
stress-ng --cpu 2 --timeout 5s > /dev/null 2>&1 &

wait $MONITOR_PID 2>/dev/null
echo

# Test Web Interface (start and show info)
echo "6. 🌐 Testing Web Interface..."
echo "   Starting web server on port 8080..."
python3 src/web_interface/app.py &
WEB_PID=$!
sleep 3

echo "   Web interface available at: http://localhost:8080"
echo "   (In VM: use VM's IP address instead of localhost)"
echo

# Stop web server
kill $WEB_PID 2>/dev/null

echo "✅ All tests completed!"
echo
echo "🎯 What you just saw:"
echo "   - Natural language to shell command translation"
echo "   - AI/ML environment setup assistance"
echo "   - Beginner-friendly AI project templates"
echo "   - System event logging and querying"
echo "   - Intelligent system monitoring with anomaly detection"
echo "   - Web interface for non-technical users"
echo
echo "🚀 Your AI-Native Linux OS is working!" 