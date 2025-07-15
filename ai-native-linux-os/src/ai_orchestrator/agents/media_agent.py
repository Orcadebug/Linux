#!/usr/bin/env python3
"""
Media Agent - Handles media playback, libraries, and related tasks
Uses tiny LLM for efficient, domain-specific processing
"""

import asyncio
import os
import subprocess
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
import mimetypes
import shutil

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent

class MediaAgent(BaseAgent):
    """
    Specialized agent for media management and playback
    - Media playback control
    - Library organization
    - Media conversion
    - Playlist management
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "Media"
        self.tiny_model = "phi3:mini"  # Tiny LLM for this domain
        self.capabilities = [
            "play_media",
            "organize_library",
            "convert_media",
            "manage_playlists",
            "media_info",
            "streaming_control"
        ]
        self.media_extensions = {
            'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff']
        }
        self.media_players = self._detect_media_players()
        
    def _detect_media_players(self) -> Dict[str, str]:
        """Detect available media players"""
        players = {}
        player_commands = {
            'vlc': 'vlc --version',
            'mpv': 'mpv --version',
            'mplayer': 'mplayer -version',
            'ffplay': 'ffplay -version',
            'audacious': 'audacious --version',
            'rhythmbox': 'rhythmbox --version'
        }
        
        for player, check_cmd in player_commands.items():
            try:
                subprocess.run(check_cmd.split(), capture_output=True, check=True)
                players[player] = player
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        return players
    
    async def handle(self, query: str) -> str:
        """Handle media queries with tiny LLM"""
        try:
            # Use tiny LLM for domain-specific classification
            if OLLAMA_AVAILABLE:
                classification_prompt = f"""
                Classify this media query into one category:
                - play: Play media files or control playback
                - organize: Organize media library
                - convert: Convert media formats
                - playlist: Manage playlists
                - info: Get media information
                - stream: Control streaming services
                
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
            if category == 'play':
                return await self._handle_play(query)
            elif category == 'organize':
                return await self._handle_organize(query)
            elif category == 'convert':
                return await self._handle_convert(query)
            elif category == 'playlist':
                return await self._handle_playlist(query)
            elif category == 'info':
                return await self._handle_info(query)
            elif category == 'stream':
                return await self._handle_stream(query)
            else:
                return await self._handle_general(query)
                
        except Exception as e:
            logging.error(f"MediaAgent error: {e}")
            return f"Error processing media request: {str(e)}"
    
    def _fallback_classify(self, query: str) -> str:
        """Fallback classification without LLM"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['play', 'start', 'pause', 'stop', 'volume']):
            return 'play'
        elif any(word in query_lower for word in ['organize', 'sort', 'library', 'collection']):
            return 'organize'
        elif any(word in query_lower for word in ['convert', 'format', 'encode', 'transcode']):
            return 'convert'
        elif any(word in query_lower for word in ['playlist', 'queue', 'list']):
            return 'playlist'
        elif any(word in query_lower for word in ['info', 'metadata', 'details', 'properties']):
            return 'info'
        elif any(word in query_lower for word in ['stream', 'streaming', 'youtube', 'spotify']):
            return 'stream'
        else:
            return 'general'
    
    async def _handle_play(self, query: str) -> str:
        """Handle media playback"""
        try:
            # Extract media file or control command
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the media file path or playback command from this query:
                "{query}"
                
                If it's a file path, respond with just the path.
                If it's a control command (play/pause/stop), respond with the command.
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                command_or_file = response['response'].strip()
            else:
                # Simple pattern matching
                words = query.lower().split()
                command_or_file = None
                
                for word in words:
                    if word in ['play', 'pause', 'stop', 'next', 'previous']:
                        command_or_file = word
                        break
                
                if not command_or_file:
                    # Look for file path
                    for word in words:
                        if '.' in word and any(ext in word for ext_list in self.media_extensions.values() for ext in ext_list):
                            command_or_file = word
                            break
            
            if not command_or_file:
                return "Please specify a media file to play or a playback command."
            
            # Handle playback commands
            if command_or_file in ['play', 'pause', 'stop', 'next', 'previous']:
                return await self._handle_playback_control(command_or_file)
            
            # Handle file playback
            media_file = os.path.expanduser(command_or_file)
            if not os.path.exists(media_file):
                # Try to find in common media directories
                media_dirs = [
                    os.path.expanduser("~/Music"),
                    os.path.expanduser("~/Videos"),
                    os.path.expanduser("~/Pictures"),
                    os.path.expanduser("~/Downloads")
                ]
                
                for media_dir in media_dirs:
                    if os.path.exists(media_dir):
                        for root, dirs, files in os.walk(media_dir):
                            for file in files:
                                if command_or_file.lower() in file.lower():
                                    media_file = os.path.join(root, file)
                                    break
            
            if not os.path.exists(media_file):
                return f"Media file not found: {command_or_file}"
            
            # Play using available player
            if 'vlc' in self.media_players:
                subprocess.Popen(['vlc', media_file])
                return f"🎵 Playing {os.path.basename(media_file)} with VLC"
            elif 'mpv' in self.media_players:
                subprocess.Popen(['mpv', media_file])
                return f"🎵 Playing {os.path.basename(media_file)} with MPV"
            elif 'mplayer' in self.media_players:
                subprocess.Popen(['mplayer', media_file])
                return f"🎵 Playing {os.path.basename(media_file)} with MPlayer"
            else:
                return "No media player found. Please install VLC, MPV, or MPlayer."
                
        except Exception as e:
            return f"Error playing media: {str(e)}"
    
    async def _handle_playback_control(self, command: str) -> str:
        """Handle playback control commands"""
        try:
            # This is a simplified implementation
            # In a real system, you'd need to communicate with the running media player
            control_messages = {
                'play': "▶️ Playback resumed",
                'pause': "⏸️ Playback paused",
                'stop': "⏹️ Playback stopped",
                'next': "⏭️ Playing next track",
                'previous': "⏮️ Playing previous track"
            }
            
            return control_messages.get(command, f"Playback command: {command}")
            
        except Exception as e:
            return f"Error controlling playback: {str(e)}"
    
    async def _handle_organize(self, query: str) -> str:
        """Handle media library organization"""
        try:
            media_dir = self._extract_directory(query) or os.path.expanduser("~/Music")
            
            if not os.path.exists(media_dir):
                return f"Media directory {media_dir} does not exist."
            
            organized_count = 0
            created_folders = set()
            
            # Create media type folders
            for media_type in self.media_extensions.keys():
                type_path = os.path.join(media_dir, media_type.title())
                if not os.path.exists(type_path):
                    os.makedirs(type_path)
                    created_folders.add(media_type.title())
            
            # Organize files by type
            for item in os.listdir(media_dir):
                item_path = os.path.join(media_dir, item)
                
                if os.path.isfile(item_path):
                    file_ext = os.path.splitext(item)[1].lower()
                    
                    # Find appropriate media type
                    for media_type, extensions in self.media_extensions.items():
                        if file_ext in extensions:
                            dest_folder = os.path.join(media_dir, media_type.title())
                            dest_path = os.path.join(dest_folder, item)
                            
                            if os.path.dirname(item_path) != dest_folder:
                                shutil.move(item_path, dest_path)
                                organized_count += 1
                            break
            
            result = f"🎼 Organized {organized_count} media files"
            if created_folders:
                result += f"\n📂 Created folders: {', '.join(created_folders)}"
            
            return result
            
        except Exception as e:
            return f"Error organizing media library: {str(e)}"
    
    async def _handle_convert(self, query: str) -> str:
        """Handle media conversion"""
        try:
            # Check if ffmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return "FFmpeg is required for media conversion but not found. Please install it."
            
            # Extract source and target format
            if OLLAMA_AVAILABLE:
                extract_prompt = f"""
                Extract the source file and target format from this conversion request:
                "{query}"
                
                Respond in format: "source_file:target_format" (e.g., "video.avi:mp4")
                """
                response = ollama.generate(model=self.tiny_model, prompt=extract_prompt)
                parts = response['response'].strip().split(':')
                if len(parts) == 2:
                    source_file, target_format = parts
                else:
                    return "Please specify the source file and target format."
            else:
                return "Media conversion requires more specific input. Please specify source file and target format."
            
            source_path = os.path.expanduser(source_file)
            if not os.path.exists(source_path):
                return f"Source file not found: {source_file}"
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            output_path = os.path.join(os.path.dirname(source_path), f"{base_name}.{target_format}")
            
            # Convert using ffmpeg
            cmd = ['ffmpeg', '-i', source_path, output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"✅ Successfully converted {source_file} to {target_format}"
            else:
                return f"❌ Conversion failed: {result.stderr}"
                
        except Exception as e:
            return f"Error converting media: {str(e)}"
    
    async def _handle_playlist(self, query: str) -> str:
        """Handle playlist management"""
        try:
            # Simple playlist management
            playlist_dir = os.path.expanduser("~/Playlists")
            if not os.path.exists(playlist_dir):
                os.makedirs(playlist_dir)
            
            if "create" in query.lower():
                # Create new playlist
                playlist_name = "new_playlist"
                playlist_file = os.path.join(playlist_dir, f"{playlist_name}.m3u")
                
                with open(playlist_file, 'w') as f:
                    f.write("#EXTM3U\n")
                
                return f"🎵 Created playlist: {playlist_name}"
            
            elif "list" in query.lower():
                # List playlists
                playlists = [f for f in os.listdir(playlist_dir) if f.endswith('.m3u')]
                if playlists:
                    return f"🎵 Available playlists:\n" + "\n".join([f"• {p}" for p in playlists])
                else:
                    return "No playlists found."
            
            else:
                return "Playlist management: create, list, or specify playlist name."
                
        except Exception as e:
            return f"Error managing playlist: {str(e)}"
    
    async def _handle_info(self, query: str) -> str:
        """Handle media information requests"""
        try:
            # Extract media file
            media_file = self._extract_media_file(query)
            if not media_file or not os.path.exists(media_file):
                return "Please specify a valid media file."
            
            # Get basic file info
            file_size = os.path.getsize(media_file)
            file_size_mb = file_size / (1024 * 1024)
            
            info = f"📄 Media Information:\n"
            info += f"• File: {os.path.basename(media_file)}\n"
            info += f"• Size: {file_size_mb:.1f} MB\n"
            info += f"• Type: {mimetypes.guess_type(media_file)[0] or 'Unknown'}\n"
            
            # Try to get more detailed info with ffprobe if available
            try:
                result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', media_file], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    import json
                    metadata = json.loads(result.stdout)
                    if 'format' in metadata:
                        duration = float(metadata['format'].get('duration', 0))
                        info += f"• Duration: {duration:.1f} seconds\n"
            except:
                pass
            
            return info
            
        except Exception as e:
            return f"Error getting media info: {str(e)}"
    
    async def _handle_stream(self, query: str) -> str:
        """Handle streaming service control"""
        return "🌐 Streaming service integration coming soon. Currently supports local media playback."
    
    async def _handle_general(self, query: str) -> str:
        """Handle general media queries"""
        if OLLAMA_AVAILABLE:
            try:
                general_prompt = f"""
                You are a media management assistant. Help with this query:
                "{query}"
                
                Provide a helpful response about media playback, organization, or management.
                """
                response = ollama.generate(model=self.tiny_model, prompt=general_prompt)
                return response['response']
            except Exception as e:
                logging.warning(f"General LLM response failed: {e}")
        
        return "I can help with media tasks like playing files, organizing your media library, converting formats, and managing playlists. What would you like to do?"
    
    def _extract_directory(self, query: str) -> Optional[str]:
        """Extract directory path from query"""
        words = query.split()
        for word in words:
            if word.startswith('/') or word.startswith('~'):
                return os.path.expanduser(word)
        return None
    
    def _extract_media_file(self, query: str) -> Optional[str]:
        """Extract media file path from query"""
        words = query.split()
        for word in words:
            if any(ext in word.lower() for ext_list in self.media_extensions.values() for ext in ext_list):
                return os.path.expanduser(word)
        return None

# Compatibility alias
Agent = MediaAgent 