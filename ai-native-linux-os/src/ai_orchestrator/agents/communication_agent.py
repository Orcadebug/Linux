#!/usr/bin/env python3
"""
Communication Agent - Manages emails, messages, and calls
Uses tiny LLM for efficient, domain-specific processing
"""

import asyncio
import os
import subprocess
import logging
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent

class CommunicationAgent(BaseAgent):
    """
    Specialized agent for communication management
    - Email management
    - Message handling
    - Call management
    - Notification control
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "Communication"
        self.tiny_model = "phi3:mini"  # Tiny LLM for this domain
        self.capabilities = [
            "send_email",
            "check_email",
            "manage_messages",
            "handle_calls",
            "manage_notifications",
            "contact_management"
        ]
        self.config_file = os.path.expanduser("~/.config/ai-native-linux/communication.json")
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load communication configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Could not load communication config: {e}")
        
        return {
            "email": {
                "smtp_server": "",
                "smtp_port": 587,
                "imap_server": "",
                "imap_port": 993,
                "username": "",
                "password": ""  # Should be encrypted in production
            },
            "contacts": {},
            "notifications": {
                "enabled": True,
                "sound": True
            }
        }
    
    def _save_config(self):
        """Save communication configuration"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Could not save communication config: {e}")
    
    async def handle(self, query: str) -> str:
        """Handle communication queries with tiny LLM"""
        try:
            # Use tiny LLM for domain-specific classification
            if OLLAMA_AVAILABLE:
                classification_prompt = f"""
                Classify this communication query into one category:
                - email: Send, check, or manage emails
                - message: Handle messages or chat
                - call: Make or manage calls
                - notification: Manage notifications
                - contact: Manage contacts
                - config: Configure communication settings
                
                Query: {query}
                
                Respond with just the category name.
                """
                
                try:
                    response = ollama.generate(model=self.tiny_model, prompt=classification_prompt)
                    category = response['response'].strip().lower()
                except Exception as e:
                    logging.warning(f"LLM classification failed: {e}")
                    category = self._fallback_classify(query)
            else:
                category = self._fallback_classify(query)
            
            # Route to appropriate handler
            if category == 'email':
                return await self._handle_email(query)
            elif category == 'message':
                return await self._handle_message(query)
            elif category == 'call':
                return await self._handle_call(query)
            elif category == 'notification':
                return await self._handle_notification(query)
            elif category == 'contact':
                return await self._handle_contact(query)
            elif category == 'config':
                return await self._handle_config(query)
            else:
                return await self._handle_general(query)
                
        except Exception as e:
            logging.error(f"CommunicationAgent error: {e}")
            return f"Error processing communication request: {str(e)}"
    
    def _fallback_classify(self, query: str) -> str:
        """Fallback classification without LLM"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['email', 'mail', 'send', 'inbox']):
            return 'email'
        elif any(word in query_lower for word in ['message', 'text', 'chat', 'sms']):
            return 'message'
        elif any(word in query_lower for word in ['call', 'phone', 'dial']):
            return 'call'
        elif any(word in query_lower for word in ['notification', 'alert', 'notify']):
            return 'notification'
        elif any(word in query_lower for word in ['contact', 'address', 'book']):
            return 'contact'
        elif any(word in query_lower for word in ['config', 'setup', 'configure']):
            return 'config'
        else:
            return 'general'
    
    async def _handle_email(self, query: str) -> str:
        """Handle email operations"""
        try:
            if not self.config["email"]["username"]:
                return "📧 Email not configured. Please set up your email account first."
            
            if "send" in query.lower():
                return await self._send_email(query)
            elif "check" in query.lower() or "inbox" in query.lower():
                return await self._check_email()
            else:
                return "📧 Email options: send email, check inbox"
                
        except Exception as e:
            return f"Error handling email: {str(e)}"
    
    async def _send_email(self, query: str) -> str:
        """Send email"""
        try:
            # Extract recipient and message using LLM
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the recipient and message from this email request:
                "{query}"
                
                Respond in format: "recipient:subject:message"
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                parts = response['response'].strip().split(':')
                if len(parts) >= 3:
                    recipient, subject, message = parts[0], parts[1], ':'.join(parts[2:])
                else:
                    return "Please specify recipient, subject, and message."
            else:
                return "Email sending requires more specific input. Please specify recipient, subject, and message."
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]["username"]
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.config["email"]["smtp_server"], self.config["email"]["smtp_port"])
            server.starttls()
            server.login(self.config["email"]["username"], self.config["email"]["password"])
            
            text = msg.as_string()
            server.sendmail(self.config["email"]["username"], recipient, text)
            server.quit()
            
            return f"✅ Email sent to {recipient}"
            
        except Exception as e:
            return f"Error sending email: {str(e)}"
    
    async def _check_email(self) -> str:
        """Check email inbox"""
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.config["email"]["imap_server"], self.config["email"]["imap_port"])
            mail.login(self.config["email"]["username"], self.config["email"]["password"])
            mail.select('inbox')
            
            # Search for unread emails
            result, data = mail.search(None, 'UNSEEN')
            
            if result == 'OK':
                email_ids = data[0].split()
                unread_count = len(email_ids)
                
                if unread_count > 0:
                    result_msg = f"📧 You have {unread_count} unread emails:\n"
                    
                    # Get details of first few emails
                    for i, email_id in enumerate(email_ids[:5]):  # Show first 5
                        result, data = mail.fetch(email_id, '(RFC822)')
                        raw_email = data[0][1]
                        email_message = email.message_from_bytes(raw_email)
                        
                        subject = email_message['Subject'] or 'No Subject'
                        sender = email_message['From']
                        
                        result_msg += f"• From: {sender}\n  Subject: {subject}\n"
                    
                    if unread_count > 5:
                        result_msg += f"... and {unread_count - 5} more"
                else:
                    result_msg = "📧 No unread emails"
            else:
                result_msg = "Error checking email"
            
            mail.close()
            mail.logout()
            
            return result_msg
            
        except Exception as e:
            return f"Error checking email: {str(e)}"
    
    async def _handle_message(self, query: str) -> str:
        """Handle messaging operations"""
        try:
            # This is a placeholder for messaging functionality
            # In a real implementation, you'd integrate with messaging services
            
            if "send" in query.lower():
                return "📱 Message sending functionality coming soon. Currently supports email."
            elif "check" in query.lower():
                return "📱 Message checking functionality coming soon."
            else:
                return "📱 Messaging features: send message, check messages"
                
        except Exception as e:
            return f"Error handling messages: {str(e)}"
    
    async def _handle_call(self, query: str) -> str:
        """Handle call operations"""
        try:
            # This is a placeholder for call functionality
            # In a real implementation, you'd integrate with VoIP services
            
            if "make" in query.lower() or "call" in query.lower():
                return "📞 Call functionality coming soon. Please use your phone app."
            elif "history" in query.lower():
                return "📞 Call history functionality coming soon."
            else:
                return "📞 Call features: make call, call history"
                
        except Exception as e:
            return f"Error handling calls: {str(e)}"
    
    async def _handle_notification(self, query: str) -> str:
        """Handle notification management"""
        try:
            if "enable" in query.lower():
                self.config["notifications"]["enabled"] = True
                self._save_config()
                return "🔔 Notifications enabled"
            elif "disable" in query.lower():
                self.config["notifications"]["enabled"] = False
                self._save_config()
                return "🔕 Notifications disabled"
            elif "status" in query.lower():
                status = "enabled" if self.config["notifications"]["enabled"] else "disabled"
                return f"🔔 Notifications are {status}"
            else:
                return "🔔 Notification options: enable, disable, status"
                
        except Exception as e:
            return f"Error managing notifications: {str(e)}"
    
    async def _handle_contact(self, query: str) -> str:
        """Handle contact management"""
        try:
            if "add" in query.lower():
                # Extract contact info
                if OLLAMA_AVAILABLE:
                    extract_prompt = f"""
                    Extract the contact name and email from this request:
                    "{query}"
                    
                    Respond in format: "name:email"
                    """
                    response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                    parts = response['response'].strip().split(':')
                    if len(parts) == 2:
                        name, email = parts
                        self.config["contacts"][name] = {"email": email}
                        self._save_config()
                        return f"👤 Added contact: {name} ({email})"
                    else:
                        return "Please specify contact name and email."
                else:
                    return "Contact management requires more specific input."
            
            elif "list" in query.lower():
                if self.config["contacts"]:
                    contact_list = "\n".join([f"• {name}: {info['email']}" 
                                            for name, info in self.config["contacts"].items()])
                    return f"👥 Contacts:\n{contact_list}"
                else:
                    return "👥 No contacts found"
            
            else:
                return "👥 Contact options: add contact, list contacts"
                
        except Exception as e:
            return f"Error managing contacts: {str(e)}"
    
    async def _handle_config(self, query: str) -> str:
        """Handle configuration"""
        try:
            if "email" in query.lower():
                return """📧 Email Configuration:
Please set up your email account:
1. SMTP server and port
2. IMAP server and port  
3. Username and password

Configuration file: ~/.config/ai-native-linux/communication.json"""
            else:
                return "⚙️ Configuration options: email setup"
                
        except Exception as e:
            return f"Error with configuration: {str(e)}"
    
    async def _handle_general(self, query: str) -> str:
        """Handle general communication queries"""
        if OLLAMA_AVAILABLE:
            try:
                general_prompt = f"""
                You are a communication assistant. Help with this query:
                "{query}"
                
                Provide a helpful response about email, messaging, or communication.
                """
                response = ollama.generate(model=self.tiny_model, prompt=general_prompt)
                return response['response']
            except Exception as e:
                logging.warning(f"General LLM response failed: {e}")
        
        return "I can help with communication tasks like sending emails, checking messages, managing contacts, and handling notifications. What would you like to do?"

# Compatibility alias
Agent = CommunicationAgent 