#!/usr/bin/env python3
"""
AI-Native Linux OS - Web Interface for Non-Technical Users
A simple web interface that makes AI/ML accessible to everyone
"""

from flask import Flask, render_template, request, jsonify, session
import os
import sys
import subprocess
import json
from pathlib import Path

# Add the parent directory to the path so we can import our AI shell
sys.path.append(str(Path(__file__).parent.parent))
from ai_shell.ai_shell import AIShellAssistant

app = Flask(__name__)
app.secret_key = 'ai-native-linux-os-secret-key'

class WebAIInterface:
    def __init__(self):
        self.ai_assistant = AIShellAssistant()
        self.project_templates = {
            'image_recognition': {
                'title': '📸 Photo Recognition',
                'description': 'Teach your computer to recognize objects in photos',
                'difficulty': 'Beginner',
                'time': '15 minutes',
                'examples': ['Recognize cats vs dogs', 'Identify flowers', 'Detect faces']
            },
            'chatbot': {
                'title': '💬 AI Chatbot',
                'description': 'Build your own AI assistant that can chat',
                'difficulty': 'Beginner',
                'time': '10 minutes',
                'examples': ['Customer service bot', 'Personal assistant', 'Quiz bot']
            },
            'prediction': {
                'title': '🔮 Future Predictor',
                'description': 'Predict prices, sales, weather, and more',
                'difficulty': 'Intermediate',
                'time': '20 minutes',
                'examples': ['House prices', 'Stock prices', 'Sales forecast']
            },
            'text_analysis': {
                'title': '📝 Text Analyzer',
                'description': 'Understand emotions and meaning in text',
                'difficulty': 'Beginner',
                'time': '12 minutes',
                'examples': ['Review sentiment', 'Email classification', 'Social media monitoring']
            }
        }

web_interface = WebAIInterface()

@app.route('/')
def home():
    """Main dashboard for non-technical users"""
    return render_template('dashboard.html', 
                         projects=web_interface.project_templates,
                         user_level='beginner')

@app.route('/project/<project_type>')
def project_setup(project_type):
    """Setup page for a specific project"""
    if project_type not in web_interface.project_templates:
        return "Project not found", 404
    
    project = web_interface.project_templates[project_type]
    return render_template('project_setup.html', 
                         project=project,
                         project_type=project_type)

@app.route('/api/start_project', methods=['POST'])
def start_project():
    """Start a project setup via API"""
    data = request.get_json()
    project_type = data.get('project_type')
    
    if not project_type:
        return jsonify({'error': 'Project type required'}), 400
    
    # Map project types to AI shell commands
    command_map = {
        'image_recognition': 'teach computer to recognize photos',
        'chatbot': 'build a chatbot',
        'prediction': 'predict house prices',
        'text_analysis': 'analyze customer reviews'
    }
    
    command = command_map.get(project_type)
    if not command:
        return jsonify({'error': 'Unknown project type'}), 400
    
    try:
        # Get the setup instructions from our AI shell
        instructions = web_interface.ai_assistant.translate_natural_language(command)
        
        return jsonify({
            'success': True,
            'instructions': instructions,
            'next_steps': [
                'Copy and paste the commands into your terminal',
                'Follow the step-by-step instructions',
                'Come back here when you\'re ready for the next step'
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask_ai', methods=['POST'])
def ask_ai():
    """Natural language interface to AI assistant"""
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    try:
        # Use our AI shell to process the question
        response = web_interface.ai_assistant.translate_natural_language(question)
        
        return jsonify({
            'success': True,
            'response': response,
            'type': 'command' if response.startswith('#') else 'explanation'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tutorial')
def tutorial():
    """Interactive AI tutorial for beginners"""
    return render_template('tutorial.html')

@app.route('/api/tutorial_step', methods=['POST'])
def tutorial_step():
    """Get tutorial step content"""
    data = request.get_json()
    step = data.get('step', 1)
    
    tutorial_steps = {
        1: {
            'title': 'What is AI?',
            'content': 'AI is like teaching a computer to think and learn, just like how you learned to recognize cats by seeing many cat photos!',
            'example': 'Show computer 1000 cat photos → Computer learns → Now it can spot cats in new photos!',
            'action': 'Click Next to see how we teach computers'
        },
        2: {
            'title': 'How do we teach computers?',
            'content': 'We show them lots of examples, let them practice, and correct their mistakes. Just like learning to ride a bike!',
            'example': 'Teaching computer to detect spam emails: Show 10,000 spam emails + 10,000 good emails → Computer learns patterns → Now it can spot spam!',
            'action': 'Ready to build your first AI? Click Next!'
        },
        3: {
            'title': 'Your first AI project',
            'content': 'Let\'s start with something fun - teaching your computer to recognize photos!',
            'example': 'We\'ll use 50,000 practice photos of animals, cars, and planes. Your computer will learn to tell them apart!',
            'action': 'Click "Start Photo Recognition Project" below'
        }
    }
    
    return jsonify(tutorial_steps.get(step, {'error': 'Step not found'}))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) 