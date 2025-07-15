#!/usr/bin/env python3
"""
File and Storage Agent - Manages file organization, cleanup, and storage tasks
Uses tiny LLM for efficient, domain-specific processing
"""

import asyncio
import os
import shutil
import logging
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import mimetypes

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent

class FileStorageAgent(BaseAgent):
    """
    Specialized agent for file and storage management
    - File organization and categorization
    - Duplicate file detection and cleanup
    - Storage analysis and optimization
    - Backup management
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "FileStorage"
        self.tiny_model = "phi3:mini"  # Tiny LLM for this domain
        self.capabilities = [
            "organize_files",
            "cleanup_duplicates",
            "analyze_storage",
            "create_backup",
            "categorize_files",
            "find_large_files"
        ]
        self.file_categories = {
            'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
            'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'],
            'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'code': ['.py', '.js', '.html', '.css', '.cpp', '.java', '.php'],
            'executables': ['.exe', '.msi', '.deb', '.rpm', '.dmg', '.app']
        }
        
    async def handle(self, query: str) -> str:
        """Handle file and storage queries with tiny LLM"""
        try:
            # Use tiny LLM for domain-specific classification
            if OLLAMA_AVAILABLE:
                classification_prompt = f"""
                Classify this file/storage management query into one category:
                - organize: Organize files into folders
                - cleanup: Clean up duplicates or unnecessary files
                - analyze: Analyze storage usage
                - backup: Create or manage backups
                - categorize: Categorize files by type
                - find: Find large files or specific files
                
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
            if category == 'organize':
                return await self._handle_organize(query)
            elif category == 'cleanup':
                return await self._handle_cleanup(query)
            elif category == 'analyze':
                return await self._handle_analyze(query)
            elif category == 'backup':
                return await self._handle_backup(query)
            elif category == 'categorize':
                return await self._handle_categorize(query)
            elif category == 'find':
                return await self._handle_find(query)
            else:
                return await self._handle_general(query)
                
        except Exception as e:
            logging.error(f"FileStorageAgent error: {e}")
            return f"Error processing file/storage request: {str(e)}"
    
    def _fallback_classify(self, query: str) -> str:
        """Fallback classification without LLM"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['organize', 'sort', 'arrange', 'folders']):
            return 'organize'
        elif any(word in query_lower for word in ['cleanup', 'clean', 'duplicate', 'remove']):
            return 'cleanup'
        elif any(word in query_lower for word in ['analyze', 'usage', 'space', 'size']):
            return 'analyze'
        elif any(word in query_lower for word in ['backup', 'copy', 'archive']):
            return 'backup'
        elif any(word in query_lower for word in ['categorize', 'category', 'type']):
            return 'categorize'
        elif any(word in query_lower for word in ['find', 'search', 'large', 'big']):
            return 'find'
        else:
            return 'general'
    
    async def _handle_organize(self, query: str) -> str:
        """Handle file organization"""
        try:
            # Extract target directory
            target_dir = self._extract_directory(query) or os.path.expanduser("~")
            
            if not os.path.exists(target_dir):
                return f"Directory {target_dir} does not exist."
            
            organized_count = 0
            created_folders = set()
            
            # Create category folders
            for category in self.file_categories.keys():
                category_path = os.path.join(target_dir, category.title())
                if not os.path.exists(category_path):
                    os.makedirs(category_path)
                    created_folders.add(category.title())
            
            # Organize files
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                
                if os.path.isfile(item_path):
                    file_ext = os.path.splitext(item)[1].lower()
                    
                    # Find appropriate category
                    for category, extensions in self.file_categories.items():
                        if file_ext in extensions:
                            dest_folder = os.path.join(target_dir, category.title())
                            dest_path = os.path.join(dest_folder, item)
                            
                            # Move file if not already in correct location
                            if os.path.dirname(item_path) != dest_folder:
                                shutil.move(item_path, dest_path)
                                organized_count += 1
                            break
            
            result = f"📁 Organized {organized_count} files"
            if created_folders:
                result += f"\n📂 Created folders: {', '.join(created_folders)}"
            
            return result
            
        except Exception as e:
            return f"Error organizing files: {str(e)}"
    
    async def _handle_cleanup(self, query: str) -> str:
        """Handle file cleanup and duplicate removal"""
        try:
            target_dir = self._extract_directory(query) or os.path.expanduser("~")
            
            if not os.path.exists(target_dir):
                return f"Directory {target_dir} does not exist."
            
            # Find duplicates
            duplicates = self._find_duplicates(target_dir)
            removed_count = 0
            space_saved = 0
            
            for file_hash, file_list in duplicates.items():
                if len(file_list) > 1:
                    # Keep the first file, remove others
                    for duplicate_file in file_list[1:]:
                        try:
                            file_size = os.path.getsize(duplicate_file)
                            os.remove(duplicate_file)
                            removed_count += 1
                            space_saved += file_size
                        except Exception as e:
                            logging.warning(f"Could not remove {duplicate_file}: {e}")
            
            # Clean up empty directories
            self._remove_empty_dirs(target_dir)
            
            space_saved_mb = space_saved / (1024 * 1024)
            return f"🧹 Cleanup completed:\n• Removed {removed_count} duplicate files\n• Freed {space_saved_mb:.1f} MB of space"
            
        except Exception as e:
            return f"Error during cleanup: {str(e)}"
    
    async def _handle_analyze(self, query: str) -> str:
        """Handle storage analysis"""
        try:
            target_dir = self._extract_directory(query) or os.path.expanduser("~")
            
            if not os.path.exists(target_dir):
                return f"Directory {target_dir} does not exist."
            
            # Analyze directory
            total_size = 0
            file_count = 0
            dir_count = 0
            type_stats = defaultdict(lambda: {'count': 0, 'size': 0})
            
            for root, dirs, files in os.walk(target_dir):
                dir_count += len(dirs)
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        file_count += 1
                        
                        # Categorize by extension
                        ext = os.path.splitext(file)[1].lower()
                        type_stats[ext]['count'] += 1
                        type_stats[ext]['size'] += file_size
                    except Exception:
                        continue
            
            # Format results
            total_size_mb = total_size / (1024 * 1024)
            result = f"📊 Storage Analysis for {target_dir}:\n"
            result += f"• Total Size: {total_size_mb:.1f} MB\n"
            result += f"• Files: {file_count}\n"
            result += f"• Directories: {dir_count}\n"
            
            # Top file types by size
            sorted_types = sorted(type_stats.items(), key=lambda x: x[1]['size'], reverse=True)[:5]
            if sorted_types:
                result += "\n📈 Top file types by size:\n"
                for ext, stats in sorted_types:
                    size_mb = stats['size'] / (1024 * 1024)
                    result += f"• {ext or 'no extension'}: {stats['count']} files, {size_mb:.1f} MB\n"
            
            return result
            
        except Exception as e:
            return f"Error analyzing storage: {str(e)}"
    
    async def _handle_backup(self, query: str) -> str:
        """Handle backup operations"""
        try:
            source_dir = self._extract_directory(query) or os.path.expanduser("~")
            backup_dir = os.path.join(os.path.expanduser("~"), "Backups")
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # Create backup
            shutil.copytree(source_dir, backup_path, ignore=shutil.ignore_patterns('*.tmp', '*.log'))
            
            # Calculate backup size
            backup_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, dirnames, filenames in os.walk(backup_path)
                            for filename in filenames)
            
            backup_size_mb = backup_size / (1024 * 1024)
            return f"💾 Backup created successfully:\n• Location: {backup_path}\n• Size: {backup_size_mb:.1f} MB"
            
        except Exception as e:
            return f"Error creating backup: {str(e)}"
    
    async def _handle_categorize(self, query: str) -> str:
        """Handle file categorization"""
        try:
            target_dir = self._extract_directory(query) or os.path.expanduser("~")
            
            if not os.path.exists(target_dir):
                return f"Directory {target_dir} does not exist."
            
            category_stats = defaultdict(int)
            
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isfile(item_path):
                    file_ext = os.path.splitext(item)[1].lower()
                    
                    # Find category
                    categorized = False
                    for category, extensions in self.file_categories.items():
                        if file_ext in extensions:
                            category_stats[category] += 1
                            categorized = True
                            break
                    
                    if not categorized:
                        category_stats['other'] += 1
            
            result = f"📋 File Categories in {target_dir}:\n"
            for category, count in category_stats.items():
                result += f"• {category.title()}: {count} files\n"
            
            return result
            
        except Exception as e:
            return f"Error categorizing files: {str(e)}"
    
    async def _handle_find(self, query: str) -> str:
        """Handle file finding operations"""
        try:
            target_dir = self._extract_directory(query) or os.path.expanduser("~")
            
            if not os.path.exists(target_dir):
                return f"Directory {target_dir} does not exist."
            
            # Find large files (>100MB)
            large_files = []
            threshold = 100 * 1024 * 1024  # 100MB
            
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > threshold:
                            large_files.append((file_path, file_size))
                    except Exception:
                        continue
            
            # Sort by size
            large_files.sort(key=lambda x: x[1], reverse=True)
            
            if large_files:
                result = f"🔍 Large files (>100MB) found:\n"
                for file_path, size in large_files[:10]:  # Show top 10
                    size_mb = size / (1024 * 1024)
                    result += f"• {os.path.basename(file_path)}: {size_mb:.1f} MB\n"
            else:
                result = "No large files (>100MB) found."
            
            return result
            
        except Exception as e:
            return f"Error finding files: {str(e)}"
    
    async def _handle_general(self, query: str) -> str:
        """Handle general file/storage queries"""
        if OLLAMA_AVAILABLE:
            try:
                general_prompt = f"""
                You are a file management assistant. Help with this query:
                "{query}"
                
                Provide a helpful response about file organization, storage, or cleanup.
                """
                response = ollama.generate(model=self.tiny_model, prompt=general_prompt)
                return response['response']
            except Exception as e:
                logging.warning(f"General LLM response failed: {e}")
        
        return "I can help with file management tasks like organizing files, cleaning up duplicates, analyzing storage usage, and creating backups. What would you like to do?"
    
    def _extract_directory(self, query: str) -> Optional[str]:
        """Extract directory path from query"""
        # Simple pattern matching for directory paths
        words = query.split()
        for word in words:
            if word.startswith('/') or word.startswith('~'):
                return os.path.expanduser(word)
        return None
    
    def _find_duplicates(self, directory: str) -> Dict[str, List[str]]:
        """Find duplicate files by hash"""
        file_hashes = defaultdict(list)
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_hash = self._get_file_hash(file_path)
                    file_hashes[file_hash].append(file_path)
                except Exception:
                    continue
        
        return {h: files for h, files in file_hashes.items() if len(files) > 1}
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get MD5 hash of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _remove_empty_dirs(self, directory: str):
        """Remove empty directories"""
        for root, dirs, files in os.walk(directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except Exception:
                    continue

# Compatibility alias
Agent = FileStorageAgent 