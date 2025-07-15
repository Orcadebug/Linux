#!/usr/bin/env python3
"""
File Management Agent - Enhanced with async processing and efficiency improvements
"""

import asyncio
import json
import os
import shutil
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import mimetypes
import hashlib
import re

from .base_agent import BaseAgent


class FileCategory:
    """File category classification"""
    
    CATEGORIES = {
        'documents': {
            'extensions': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages'],
            'folder': 'Documents',
            'subfolders': ['PDFs', 'WordDocs', 'TextFiles']
        },
        'images': {
            'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp'],
            'folder': 'Images',
            'subfolders': ['Photos', 'Screenshots', 'Graphics']
        },
        'videos': {
            'extensions': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'],
            'folder': 'Videos',
            'subfolders': ['Movies', 'Recordings', 'Tutorials']
        },
        'audio': {
            'extensions': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
            'folder': 'Audio',
            'subfolders': ['Music', 'Podcasts', 'Recordings']
        },
        'code': {
            'extensions': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go'],
            'folder': 'Code',
            'subfolders': ['Python', 'JavaScript', 'Web', 'Projects']
        },
        'archives': {
            'extensions': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'folder': 'Archives',
            'subfolders': ['Compressed', 'Backups']
        },
        'spreadsheets': {
            'extensions': ['.xls', '.xlsx', '.csv', '.ods'],
            'folder': 'Spreadsheets',
            'subfolders': ['Excel', 'Data']
        },
    }
    
    @classmethod
    def get_category(cls, file_path: Path) -> str:
        """Get category for a file"""
        extension = file_path.suffix.lower()
        
        for category, info in cls.CATEGORIES.items():
            if extension in info['extensions']:
                return category
        
        return 'other'


class FileManagementAgent(BaseAgent):
    """Enhanced agent for intelligent file organization and management"""
    
    def __init__(self, hardware_info: Dict, security_manager, logger):
        super().__init__("file_management_agent", hardware_info, security_manager, logger)
        self.name = "File Management Agent"
        self.description = "Organizes files intelligently with safety measures and async processing"
        
        # Configuration
        self.config = {
            "safe_mode": True,
            "backup_before_move": True,
            "max_file_size": 500 * 1024 * 1024,  # 500MB
            "allowed_extensions": None,  # None means all allowed
            "forbidden_extensions": ['.exe', '.bat', '.scr', '.com'],
            "default_organize_path": str(Path.home() / "Downloads"),
            "create_backups": True,
            "dry_run": False
        }
        
        # Organization paths - limit to user's home directory for safety
        self.organize_paths = {
            'downloads': str(Path.home() / "Downloads"),
            'documents': str(Path.home() / "Documents"),
            'desktop': str(Path.home() / "Desktop"),
            'pictures': str(Path.home() / "Pictures"),
            'videos': str(Path.home() / "Videos"),
            'music': str(Path.home() / "Music")
        }
        
        # Statistics tracking
        self.stats = {
            'files_organized': 0,
            'files_moved': 0,
            'files_deleted': 0,
            'folders_created': 0,
            'duplicates_found': 0,
            'errors': 0
        }
        
        self.logger.info("Enhanced File Management Agent initialized")
    
    def _initialize_rule_patterns(self) -> Dict[str, callable]:
        """Initialize rule-based patterns for file management"""
        return {
            'organize': self._rule_organize_files,
            'cleanup': self._rule_cleanup_files,
            'duplicate': self._rule_find_duplicates,
            'sort': self._rule_sort_files,
            'backup': self._rule_backup_files,
            'delete': self._rule_delete_files,
            'move': self._rule_move_files,
            'copy': self._rule_copy_files,
            'rename': self._rule_rename_files,
            'search': self._rule_search_files
        }
    
    async def _process_task_with_llm(self, task) -> Dict:
        """Process file management task using LLM with safety checks"""
        context = {
            'available_folders': list(self.organize_paths.keys()),
            'file_categories': list(FileCategory.CATEGORIES.keys()),
            'current_config': self.config,
            'safe_mode': self.config['safe_mode']
        }
        
        prompt = f"""
File management task: {task.command}

Available organization folders: {', '.join(self.organize_paths.keys())}
File categories: {', '.join(FileCategory.CATEGORIES.keys())}
Safe mode: {self.config['safe_mode']}

Provide a specific action plan with:
1. Target directory to organize (must be within user's home directory)
2. Organization method (by type, date, project, etc.)
3. Specific folder structure to create
4. Safety measures (backup, confirmation needed)
5. Risk assessment (low/medium/high)

Be specific about folder names and file operations. Only suggest operations within the user's home directory.
"""
        
        response = await self.query_llm(prompt, context)
        
        if response:
            # Parse LLM response and execute safely
            return await self._execute_llm_plan(response, task)
        else:
            # Fallback to rules
            return await self._process_task_with_rules(task)
    
    async def _process_task_with_rules(self, task) -> Dict:
        """Process file management task using rule-based approach with async processing"""
        try:
            # Yield control for other tasks
            await asyncio.sleep(0)
        
            # Match rule pattern
            handler = self.match_rule_pattern(task.command)
        
        if handler:
                # Execute with safety checks
                if self._requires_confirmation(task.command):
                    confirm = input(f"Confirm file operation: {task.command}? (y/n): ")
                    if confirm.lower() != 'y':
                        return {
                            'success': False,
                            'result': 'Operation cancelled by user',
                            'method': 'rules'
                        }
                
                result = await handler(task.command)
                return {
                    'success': True,
                    'result': result,
                    'method': 'rules'
                }
            else:
                return {
                    'success': False,
                    'error': 'No matching rule pattern found',
                    'method': 'rules'
                }
                
        except Exception as e:
            self.logger.error(f"Rule-based processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'rules'
            }
    
    def _get_agent_description(self) -> str:
        """Get agent-specific description for prompts"""
        return "A file management agent that organizes files safely with user confirmation for destructive operations"
    
    def _get_supported_operations(self) -> List[str]:
        """Get list of operations this agent supports"""
        return [
            'organize', 'cleanup', 'duplicate', 'sort', 'backup', 
            'delete', 'move', 'copy', 'rename', 'search'
        ]
    
    def _requires_confirmation(self, command: str) -> bool:
        """Check if command requires user confirmation"""
        dangerous_keywords = ['delete', 'remove', 'rm', 'trash', 'clear']
        return any(keyword in command.lower() for keyword in dangerous_keywords)
    
    def _is_safe_path(self, path: str) -> bool:
        """Check if path is within safe boundaries (user's home directory)"""
        try:
            abs_path = Path(path).resolve()
            home_path = Path.home().resolve()
            
            # Must be within home directory
            return abs_path.is_relative_to(home_path)
        except Exception:
            return False
    
    def _is_safe_file(self, file_path: Path) -> bool:
        """Check if file is safe to process"""
        # Check file size
        if file_path.stat().st_size > self.config['max_file_size']:
            return False
        
        # Check extension
        if self.config['forbidden_extensions']:
            if file_path.suffix.lower() in self.config['forbidden_extensions']:
                return False
        
        # Check if path is safe
        return self._is_safe_path(str(file_path))
    
    async def _execute_llm_plan(self, llm_response: str, task) -> Dict:
        """Execute LLM-generated plan with safety checks"""
        try:
            # Parse LLM response (simplified - would need more sophisticated parsing)
            if 'organize' in llm_response.lower():
                return await self._rule_organize_files(task.command)
            elif 'cleanup' in llm_response.lower():
                return await self._rule_cleanup_files(task.command)
            elif 'duplicate' in llm_response.lower():
                return await self._rule_find_duplicates(task.command)
            else:
                return await self._rule_organize_files(task.command)  # Default
            
        except Exception as e:
            self.logger.error(f"LLM plan execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'llm'
            }
    
    # Rule-based handlers with async processing
    async def _rule_organize_files(self, command: str) -> str:
        """Organize files by category with async processing"""
        try:
            # Extract target directory from command or use default
            target_dir = self._extract_directory_from_command(command)
            if not target_dir or not self._is_safe_path(target_dir):
                target_dir = self.organize_paths['downloads']
            
            target_path = Path(target_dir)
            if not target_path.exists():
                return f"Directory {target_dir} does not exist"
            
            organized_count = 0
            created_folders = []
            
            # Process files asynchronously
            files = list(target_path.glob('*'))
            
            for file_path in files:
                await asyncio.sleep(0)  # Yield control
                
                if not file_path.is_file() or not self._is_safe_file(file_path):
                    continue
                
                # Get file category
                category = FileCategory.get_category(file_path)
                
                if category == 'other':
                    continue
                
                # Create category folder
                category_info = FileCategory.CATEGORIES[category]
                category_folder = target_path / category_info['folder']
                
                if not category_folder.exists():
                    category_folder.mkdir(parents=True, exist_ok=True)
                    created_folders.append(str(category_folder))
                    self.stats['folders_created'] += 1
                
                # Move file
                destination = category_folder / file_path.name
                        
                # Handle name conflicts
                        counter = 1
                while destination.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    destination = category_folder / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                if not self.config['dry_run']:
                    shutil.move(str(file_path), str(destination))
                    organized_count += 1
                    self.stats['files_organized'] += 1
                    self.stats['files_moved'] += 1
            
            result = f"Organized {organized_count} files into {len(created_folders)} categories"
            if created_folders:
                result += f"\nCreated folders: {', '.join(created_folders)}"
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            raise e
    
    async def _rule_cleanup_files(self, command: str) -> str:
        """Clean up temporary and junk files with async processing"""
        try:
            target_dir = self._extract_directory_from_command(command)
            if not target_dir or not self._is_safe_path(target_dir):
                target_dir = self.organize_paths['downloads']
            
            target_path = Path(target_dir)
            if not target_path.exists():
                return f"Directory {target_dir} does not exist"
            
            # Define cleanup patterns
            cleanup_patterns = [
                '*.tmp', '*.temp', '*~', '*.bak', '*.old',
                '*.log', '*.cache', 'Thumbs.db', '.DS_Store'
            ]
            
            cleaned_count = 0
            cleaned_size = 0
            
            for pattern in cleanup_patterns:
                files = list(target_path.glob(pattern))
                
                for file_path in files:
                    await asyncio.sleep(0)  # Yield control
                    
                    if not self._is_safe_file(file_path):
                        continue
                
                    file_size = file_path.stat().st_size
                    
                    if not self.config['dry_run']:
                        file_path.unlink()
                        cleaned_count += 1
                        cleaned_size += file_size
                        self.stats['files_deleted'] += 1
            
            size_mb = cleaned_size / (1024 * 1024)
            return f"Cleaned up {cleaned_count} files, freed {size_mb:.1f} MB"
            
        except Exception as e:
            self.stats['errors'] += 1
            raise e
    
    async def _rule_find_duplicates(self, command: str) -> str:
        """Find duplicate files with async processing"""
        try:
            target_dir = self._extract_directory_from_command(command)
            if not target_dir or not self._is_safe_path(target_dir):
                target_dir = self.organize_paths['downloads']
            
            target_path = Path(target_dir)
            if not target_path.exists():
                return f"Directory {target_dir} does not exist"
            
            # Hash files to find duplicates
            file_hashes = defaultdict(list)
            processed_count = 0
            
            for file_path in target_path.rglob('*'):
                await asyncio.sleep(0)  # Yield control
                
                if not file_path.is_file() or not self._is_safe_file(file_path):
                    continue
                
                # Calculate hash
                hash_obj = hashlib.md5()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_obj.update(chunk)
                
                file_hash = hash_obj.hexdigest()
                file_hashes[file_hash].append(file_path)
                processed_count += 1
            
            # Find duplicates
            duplicates = {k: v for k, v in file_hashes.items() if len(v) > 1}
            duplicate_count = sum(len(files) - 1 for files in duplicates.values())
            
            self.stats['duplicates_found'] += duplicate_count
            
            if duplicates:
                result = f"Found {duplicate_count} duplicate files in {len(duplicates)} groups:\n"
                for i, (hash_val, files) in enumerate(list(duplicates.items())[:5]):  # Show first 5
                    result += f"Group {i+1}: {len(files)} files\n"
                    for file_path in files:
                        result += f"  - {file_path}\n"
                
                if len(duplicates) > 5:
                    result += f"... and {len(duplicates) - 5} more groups"
            else:
                result = f"No duplicates found in {processed_count} files"
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            raise e
    
    async def _rule_sort_files(self, command: str) -> str:
        """Sort files by date, size, or name with async processing"""
        try:
            target_dir = self._extract_directory_from_command(command)
            if not target_dir or not self._is_safe_path(target_dir):
                target_dir = self.organize_paths['downloads']
            
            target_path = Path(target_dir)
            if not target_path.exists():
                return f"Directory {target_dir} does not exist"
            
            # Determine sort method from command
            sort_method = 'date'  # default
            if 'size' in command.lower():
                sort_method = 'size'
            elif 'name' in command.lower():
                sort_method = 'name'
            
            # Create date-based folders
            if sort_method == 'date':
                sorted_count = 0
                
                for file_path in target_path.glob('*'):
                    await asyncio.sleep(0)  # Yield control
                    
                    if not file_path.is_file() or not self._is_safe_file(file_path):
                        continue
                    
                    # Get file modification date
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    year_month = mod_time.strftime('%Y-%m')
                
                    # Create year-month folder
                    date_folder = target_path / year_month
                    date_folder.mkdir(exist_ok=True)
                
                # Move file
                    destination = date_folder / file_path.name
                    if not destination.exists() and not self.config['dry_run']:
                        shutil.move(str(file_path), str(destination))
                        sorted_count += 1
                        self.stats['files_moved'] += 1
                
                return f"Sorted {sorted_count} files by date into monthly folders"
            
            return f"Sorted files by {sort_method}"
            
        except Exception as e:
            self.stats['errors'] += 1
            raise e
    
    async def _rule_backup_files(self, command: str) -> str:
        """Create backup of files with async processing"""
        try:
            target_dir = self._extract_directory_from_command(command)
            if not target_dir or not self._is_safe_path(target_dir):
                target_dir = self.organize_paths['documents']
            
            target_path = Path(target_dir)
            if not target_path.exists():
                return f"Directory {target_dir} does not exist"
            
            # Create backup folder
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = target_path.parent / backup_name
            backup_path.mkdir(exist_ok=True)
                
            backed_up_count = 0
            
            for file_path in target_path.rglob('*'):
                await asyncio.sleep(0)  # Yield control
                
                if not file_path.is_file() or not self._is_safe_file(file_path):
                    continue
                
                # Calculate relative path
                rel_path = file_path.relative_to(target_path)
                backup_file = backup_path / rel_path
                
                # Create parent directories
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                if not self.config['dry_run']:
                    shutil.copy2(str(file_path), str(backup_file))
                    backed_up_count += 1
            
            return f"Created backup with {backed_up_count} files in {backup_path}"
            
        except Exception as e:
            self.stats['errors'] += 1
            raise e
    
    async def _rule_delete_files(self, command: str) -> str:
        """Delete files with safety checks"""
        return "Delete operations require explicit confirmation for safety"
    
    async def _rule_move_files(self, command: str) -> str:
        """Move files with safety checks"""
        return "Move operations require explicit source and destination paths"
    
    async def _rule_copy_files(self, command: str) -> str:
        """Copy files with safety checks"""
        return "Copy operations require explicit source and destination paths"
    
    async def _rule_rename_files(self, command: str) -> str:
        """Rename files with safety checks"""
        return "Rename operations require explicit old and new names"
    
    async def _rule_search_files(self, command: str) -> str:
        """Search for files with async processing"""
        try:
            target_dir = self._extract_directory_from_command(command)
            if not target_dir or not self._is_safe_path(target_dir):
                target_dir = str(Path.home())
            
            target_path = Path(target_dir)
            if not target_path.exists():
                return f"Directory {target_dir} does not exist"
            
            # Extract search term from command
            search_term = self._extract_search_term(command)
            if not search_term:
                return "No search term found in command"
            
            found_files = []
            
            for file_path in target_path.rglob('*'):
                await asyncio.sleep(0)  # Yield control
                
                if not file_path.is_file():
                    continue
                
                if search_term.lower() in file_path.name.lower():
                    found_files.append(str(file_path))
                
                if len(found_files) >= 20:  # Limit results
                    break
            
            if found_files:
                result = f"Found {len(found_files)} files matching '{search_term}':\n"
                for file_path in found_files[:10]:  # Show first 10
                    result += f"  - {file_path}\n"
                
                if len(found_files) > 10:
                    result += f"... and {len(found_files) - 10} more files"
            else:
                result = f"No files found matching '{search_term}'"
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            raise e
    
    def _extract_directory_from_command(self, command: str) -> Optional[str]:
        """Extract directory path from command"""
        # Simple pattern matching - would need more sophisticated parsing
        patterns = [
            r'in\s+([^\s]+)',
            r'from\s+([^\s]+)',
            r'directory\s+([^\s]+)',
            r'folder\s+([^\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_search_term(self, command: str) -> Optional[str]:
        """Extract search term from command"""
        patterns = [
            r'search\s+for\s+([^\s]+)',
            r'find\s+([^\s]+)',
            r'look\s+for\s+([^\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
            return {
            'agent': self.name,
            'stats': self.stats,
            'config': self.config,
            'organize_paths': self.organize_paths
        }


# Testing interface
if __name__ == "__main__":
    import asyncio
    
    # Mock objects for testing
    class MockSecurityManager:
        def can_execute_task(self, task):
            return True
        
        def log_agent_activity(self, agent, action, details):
            print(f"AUDIT: {agent} - {action} - {details}")
    
    class MockTask:
        def __init__(self, command):
            self.task_id = "test-task"
            self.command = command
    
    async def test_agent():
        import logging
        
        logger = logging.getLogger("test")
        security_manager = MockSecurityManager()
        hardware_info = {"config": {}}
        
        agent = FileManagementAgent(hardware_info, security_manager, logger)
        
        # Test various scenarios
        test_cases = [
            "organize files in downloads",
            "cleanup temporary files",
            "find duplicate files",
            "sort files by date",
            "search for test files"
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case}")
            task = MockTask(test_case)
        result = await agent.execute_task(task)
        print(f"Result: {result}")
        
    asyncio.run(test_agent())