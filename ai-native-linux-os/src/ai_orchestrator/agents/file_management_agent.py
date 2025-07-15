#!/usr/bin/env python3
"""
File Management Agent - Intelligent file organization and management
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

from .base_agent import BaseAgent, extract_command_from_text, sanitize_filename, parse_file_size


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
        'presentations': {
            'extensions': ['.ppt', '.pptx', '.odp', '.key'],
            'folder': 'Presentations',
            'subfolders': ['PowerPoint', 'Keynote']
        }
    }
    
    @classmethod
    def get_category(cls, filename: str) -> str:
        """Get category for a file based on extension"""
        ext = Path(filename).suffix.lower()
        
        for category, info in cls.CATEGORIES.items():
            if ext in info['extensions']:
                return category
        
        return 'misc'


class FileManagementAgent(BaseAgent):
    """Intelligent file organization and management agent"""
    
    def __init__(self, hardware_info: Dict, security_manager, logger):
        super().__init__('file_management_agent', hardware_info, security_manager, logger)
        
        # File management configuration
        self.config = {
            'auto_organize_downloads': True,
            'create_date_folders': True,
            'duplicate_threshold_mb': 50,  # Don't auto-delete duplicates larger than 50MB
            'cleanup_temp_files': True,
            'backup_before_move': False,
            'max_file_age_days': 365,  # Files older than 1 year for cleanup suggestions
            'organize_by_project': True
        }
        
        # Common organization paths
        home = Path.home()
        self.organize_paths = {
            'downloads': home / 'Downloads',
            'documents': home / 'Documents', 
            'desktop': home / 'Desktop',
            'pictures': home / 'Pictures',
            'videos': home / 'Videos',
            'music': home / 'Music'
        }
        
        # Project patterns for smart organization
        self.project_patterns = [
            r'project[_-](\w+)',
            r'(\w+)[_-]project',
            r'assignment[_-](\w+)',
            r'homework[_-](\w+)',
            r'work[_-](\w+)',
            r'client[_-](\w+)'
        ]
    
    def _initialize_rule_patterns(self) -> Dict[str, callable]:
        """Initialize rule-based patterns for file operations"""
        return {
            'organize downloads': self._organize_downloads,
            'organize files': self._organize_current_directory,
            'clean up': self._cleanup_suggestions,
            'find duplicates': self._find_duplicates,
            'sort by date': self._sort_by_date,
            'sort by type': self._sort_by_type,
            'sort by size': self._sort_by_size,
            'create folders': self._create_folder_structure,
            'backup files': self._backup_files,
            'compress old files': self._compress_old_files
        }
    
    def _get_agent_description(self) -> str:
        """Get agent description for LLM prompts"""
        return """File Management Agent specialized in:
- Auto-organizing downloads and documents
- Smart file categorization by type, date, and project
- Duplicate file detection and cleanup
- Safe file operations with backup options
- Folder structure creation and maintenance"""
    
    def _get_supported_operations(self) -> List[str]:
        """Get list of supported operations"""
        return [
            'organize_downloads',
            'categorize_files', 
            'find_duplicates',
            'cleanup_suggestions',
            'create_folder_structure',
            'sort_files',
            'backup_files',
            'compress_archives'
        ]
    
    async def _process_task_with_llm(self, task) -> Dict:
        """Process file management task using LLM"""
        context = {
            'available_folders': list(self.organize_paths.keys()),
            'file_categories': list(FileCategory.CATEGORIES.keys()),
            'current_config': self.config
        }
        
        prompt = f"""
File management task: {task.command}

Available organization folders: {', '.join(self.organize_paths.keys())}
File categories: {', '.join(FileCategory.CATEGORIES.keys())}

Provide a specific action plan with:
1. Target directory to organize
2. Organization method (by type, date, project, etc.)
3. Specific folder structure to create
4. Safety measures (backup, confirmation needed)

Be specific about folder names and file operations.
"""
        
        response = await self.query_llm(prompt, context)
        
        if response:
            # Parse LLM response and execute
            return await self._execute_llm_plan(response, task)
        else:
            # Fallback to rules
            return await self._process_task_with_rules(task)
    
    async def _process_task_with_rules(self, task) -> Dict:
        """Process file management task using rule-based approach"""
        command = task.command.lower()
        
        # Find matching rule pattern
        handler = self.match_rule_pattern(command)
        
        if handler:
            try:
                result = await handler()
                return {
                    'success': True,
                    'result': result,
                    'method': 'rules',
                    'agent': self.agent_name
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'method': 'rules',
                    'agent': self.agent_name
                }
        else:
            return {
                'success': False,
                'error': f'No handler found for: {command}',
                'suggested_commands': list(self.rule_patterns.keys()),
                'method': 'rules',
                'agent': self.agent_name
            }
    
    async def _execute_llm_plan(self, llm_response: str, task) -> Dict:
        """Execute file management plan from LLM response"""
        try:
            # Extract action from LLM response
            if 'organize downloads' in llm_response.lower():
                result = await self._organize_downloads()
            elif 'find duplicates' in llm_response.lower():
                result = await self._find_duplicates()
            elif 'cleanup' in llm_response.lower():
                result = await self._cleanup_suggestions()
            elif 'sort by type' in llm_response.lower():
                result = await self._sort_by_type()
            elif 'sort by date' in llm_response.lower():
                result = await self._sort_by_date()
            else:
                # Generic file organization
                result = await self._organize_current_directory()
            
            return {
                'success': True,
                'result': result,
                'llm_plan': llm_response,
                'method': 'llm',
                'agent': self.agent_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'llm_plan': llm_response,
                'method': 'llm',
                'agent': self.agent_name
            }
    
    async def _organize_downloads(self) -> Dict:
        """Organize Downloads folder by file type and date"""
        downloads_path = self.organize_paths['downloads']
        
        if not downloads_path.exists():
            return {'error': 'Downloads folder not found'}
        
        organized_files = []
        errors = []
        
        try:
            # Get all files in downloads
            files = [f for f in downloads_path.iterdir() if f.is_file()]
            
            for file_path in files:
                try:
                    # Determine category and target folder
                    category = FileCategory.get_category(file_path.name)
                    year = datetime.fromtimestamp(file_path.stat().st_mtime).year
                    
                    # Create target directory structure
                    if category == 'misc':
                        target_dir = downloads_path / f"{year}/Misc"
                    else:
                        cat_info = FileCategory.CATEGORIES[category]
                        target_dir = downloads_path / f"{year}/{cat_info['folder']}"
                    
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Move file
                    target_path = target_dir / file_path.name
                    
                    # Handle name conflicts
                    counter = 1
                    while target_path.exists():
                        name = file_path.stem
                        ext = file_path.suffix
                        target_path = target_dir / f"{name}_{counter}{ext}"
                        counter += 1
                    
                    shutil.move(str(file_path), str(target_path))
                    organized_files.append({
                        'file': file_path.name,
                        'from': str(file_path.parent),
                        'to': str(target_path.parent),
                        'category': category
                    })
                    
                except Exception as e:
                    errors.append({'file': file_path.name, 'error': str(e)})
            
            return {
                'organized_count': len(organized_files),
                'error_count': len(errors),
                'organized_files': organized_files[:10],  # Limit for display
                'errors': errors,
                'summary': f"Organized {len(organized_files)} files into year/category structure"
            }
            
        except Exception as e:
            return {'error': f'Failed to organize downloads: {e}'}
    
    async def _organize_current_directory(self) -> Dict:
        """Organize files in current working directory"""
        current_path = Path.cwd()
        
        # Security check - ensure we can write to current directory
        if not os.access(current_path, os.W_OK):
            return {'error': 'No write permission for current directory'}
        
        return await self._organize_directory(current_path)
    
    async def _organize_directory(self, directory: Path) -> Dict:
        """Organize files in specified directory"""
        organized_files = []
        errors = []
        
        try:
            files = [f for f in directory.iterdir() if f.is_file()]
            
            # Group files by category
            categories = defaultdict(list)
            for file_path in files:
                category = FileCategory.get_category(file_path.name)
                categories[category].append(file_path)
            
            # Create folders and move files
            for category, file_list in categories.items():
                if category == 'misc':
                    continue  # Skip miscellaneous files
                
                cat_info = FileCategory.CATEGORIES[category]
                category_dir = directory / cat_info['folder']
                category_dir.mkdir(exist_ok=True)
                
                for file_path in file_list:
                    try:
                        target_path = category_dir / file_path.name
                        
                        # Handle conflicts
                        counter = 1
                        while target_path.exists():
                            name = file_path.stem
                            ext = file_path.suffix
                            target_path = category_dir / f"{name}_{counter}{ext}"
                            counter += 1
                        
                        shutil.move(str(file_path), str(target_path))
                        organized_files.append({
                            'file': file_path.name,
                            'category': category,
                            'moved_to': str(target_path.parent)
                        })
                        
                    except Exception as e:
                        errors.append({'file': file_path.name, 'error': str(e)})
            
            return {
                'organized_count': len(organized_files),
                'categories_created': len(categories) - (1 if 'misc' in categories else 0),
                'organized_files': organized_files,
                'errors': errors,
                'summary': f"Organized {len(organized_files)} files into {len(categories)} categories"
            }
            
        except Exception as e:
            return {'error': f'Failed to organize directory: {e}'}
    
    async def _find_duplicates(self) -> Dict:
        """Find duplicate files in organize paths"""
        duplicates = []
        total_size_saved = 0
        
        try:
            # Collect all files from organize paths
            all_files = []
            for path_name, path in self.organize_paths.items():
                if path.exists():
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            all_files.append(file_path)
            
            # Group files by size first (optimization)
            size_groups = defaultdict(list)
            for file_path in all_files:
                try:
                    size = file_path.stat().st_size
                    size_groups[size].append(file_path)
                except Exception:
                    continue
            
            # Check files with same size for duplicates
            for size, files in size_groups.items():
                if len(files) < 2:
                    continue
                
                # Calculate hashes for files of same size
                hash_groups = defaultdict(list)
                for file_path in files:
                    try:
                        file_hash = await self._calculate_file_hash(file_path)
                        hash_groups[file_hash].append(file_path)
                    except Exception:
                        continue
                
                # Report duplicates
                for file_hash, duplicate_files in hash_groups.items():
                    if len(duplicate_files) > 1:
                        # Keep the first file, mark others as duplicates
                        original = duplicate_files[0]
                        for duplicate in duplicate_files[1:]:
                            duplicates.append({
                                'original': str(original),
                                'duplicate': str(duplicate),
                                'size_mb': size / (1024 * 1024),
                                'hash': file_hash[:8]
                            })
                            total_size_saved += size
            
            return {
                'duplicate_count': len(duplicates),
                'total_size_saved_mb': total_size_saved / (1024 * 1024),
                'duplicates': duplicates[:20],  # Limit for display
                'recommendation': f"Found {len(duplicates)} duplicates. Review before deletion.",
                'large_duplicates': [d for d in duplicates if d['size_mb'] > 10]
            }
            
        except Exception as e:
            return {'error': f'Failed to find duplicates: {e}'}
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            raise Exception(f"Failed to hash {file_path}: {e}")
    
    async def _cleanup_suggestions(self) -> Dict:
        """Generate cleanup suggestions for old/temporary files"""
        suggestions = []
        total_space_recoverable = 0
        
        try:
            # Check common temporary locations
            temp_locations = [
                Path.home() / 'Downloads',
                Path.home() / 'Desktop', 
                Path('/tmp'),
                Path('/var/tmp')
            ]
            
            for location in temp_locations:
                if not location.exists():
                    continue
                
                try:
                    for file_path in location.rglob('*'):
                        if not file_path.is_file():
                            continue
                        
                        # Check file age
                        age_days = (time.time() - file_path.stat().st_mtime) / 86400
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        
                        # Suggest cleanup for old files
                        if age_days > self.config['max_file_age_days']:
                            suggestions.append({
                                'file': str(file_path),
                                'age_days': int(age_days),
                                'size_mb': round(size_mb, 2),
                                'reason': 'Very old file',
                                'location': str(location)
                            })
                            total_space_recoverable += size_mb
                        
                        # Suggest cleanup for temporary files
                        elif self._is_temp_file(file_path):
                            suggestions.append({
                                'file': str(file_path),
                                'age_days': int(age_days),
                                'size_mb': round(size_mb, 2),
                                'reason': 'Temporary file',
                                'location': str(location)
                            })
                            total_space_recoverable += size_mb
                
                except Exception:
                    continue
            
            # Sort by size (largest first)
            suggestions.sort(key=lambda x: x['size_mb'], reverse=True)
            
            return {
                'suggestion_count': len(suggestions),
                'total_space_recoverable_mb': round(total_space_recoverable, 2),
                'suggestions': suggestions[:20],  # Limit for display
                'large_files': [s for s in suggestions if s['size_mb'] > 100],
                'very_old_files': [s for s in suggestions if s['age_days'] > 730],  # 2+ years
                'recommendation': f"Review {len(suggestions)} files for cleanup to free {total_space_recoverable:.1f} MB"
            }
            
        except Exception as e:
            return {'error': f'Failed to generate cleanup suggestions: {e}'}
    
    def _is_temp_file(self, file_path: Path) -> bool:
        """Check if file appears to be temporary"""
        temp_patterns = [
            r'\.tmp$', r'\.temp$', r'\.cache$', r'\.log$',
            r'^~.*', r'\.bak$', r'\.old$', r'\.swp$',
            r'Thumbs\.db$', r'\.DS_Store$'
        ]
        
        filename = file_path.name.lower()
        return any(re.search(pattern, filename) for pattern in temp_patterns)
    
    async def _sort_by_date(self) -> Dict:
        """Sort files by modification date into year/month folders"""
        current_path = Path.cwd()
        sorted_files = []
        
        try:
            files = [f for f in current_path.iterdir() if f.is_file()]
            
            for file_path in files:
                # Get file date
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                year_month = f"{mod_time.year}/{mod_time.strftime('%m-%B')}"
                
                # Create date folder
                date_dir = current_path / year_month
                date_dir.mkdir(parents=True, exist_ok=True)
                
                # Move file
                target_path = date_dir / file_path.name
                counter = 1
                while target_path.exists():
                    name = file_path.stem
                    ext = file_path.suffix
                    target_path = date_dir / f"{name}_{counter}{ext}"
                    counter += 1
                
                shutil.move(str(file_path), str(target_path))
                sorted_files.append({
                    'file': file_path.name,
                    'date': mod_time.strftime('%Y-%m-%d'),
                    'moved_to': str(target_path.parent)
                })
            
            return {
                'sorted_count': len(sorted_files),
                'sorted_files': sorted_files,
                'summary': f"Sorted {len(sorted_files)} files by date"
            }
            
        except Exception as e:
            return {'error': f'Failed to sort by date: {e}'}
    
    async def _sort_by_type(self) -> Dict:
        """Sort files by type into category folders"""
        return await self._organize_current_directory()
    
    async def _sort_by_size(self) -> Dict:
        """Sort files by size into small/medium/large folders"""
        current_path = Path.cwd()
        sorted_files = []
        
        try:
            files = [f for f in current_path.iterdir() if f.is_file()]
            
            for file_path in files:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                
                # Determine size category
                if size_mb < 1:
                    size_category = "Small (< 1MB)"
                elif size_mb < 10:
                    size_category = "Medium (1-10MB)"
                elif size_mb < 100:
                    size_category = "Large (10-100MB)"
                else:
                    size_category = "VeryLarge (> 100MB)"
                
                # Create size folder
                size_dir = current_path / size_category
                size_dir.mkdir(exist_ok=True)
                
                # Move file
                target_path = size_dir / file_path.name
                counter = 1
                while target_path.exists():
                    name = file_path.stem
                    ext = file_path.suffix
                    target_path = size_dir / f"{name}_{counter}{ext}"
                    counter += 1
                
                shutil.move(str(file_path), str(target_path))
                sorted_files.append({
                    'file': file_path.name,
                    'size_mb': round(size_mb, 2),
                    'category': size_category,
                    'moved_to': str(target_path.parent)
                })
            
            return {
                'sorted_count': len(sorted_files),
                'sorted_files': sorted_files,
                'summary': f"Sorted {len(sorted_files)} files by size"
            }
            
        except Exception as e:
            return {'error': f'Failed to sort by size: {e}'}
    
    async def _create_folder_structure(self) -> Dict:
        """Create standard folder structure for file organization"""
        current_path = Path.cwd()
        created_folders = []
        
        try:
            # Create category folders
            for category, info in FileCategory.CATEGORIES.items():
                folder_path = current_path / info['folder']
                if not folder_path.exists():
                    folder_path.mkdir()
                    created_folders.append(str(folder_path))
                
                # Create subfolders
                for subfolder in info['subfolders']:
                    subfolder_path = folder_path / subfolder
                    if not subfolder_path.exists():
                        subfolder_path.mkdir()
                        created_folders.append(str(subfolder_path))
            
            # Create year folders
            current_year = datetime.now().year
            for year in range(current_year - 2, current_year + 1):
                year_path = current_path / str(year)
                if not year_path.exists():
                    year_path.mkdir()
                    created_folders.append(str(year_path))
            
            return {
                'created_count': len(created_folders),
                'created_folders': created_folders,
                'summary': f"Created {len(created_folders)} folders for organization"
            }
            
        except Exception as e:
            return {'error': f'Failed to create folder structure: {e}'}
    
    async def _backup_files(self) -> Dict:
        """Create backup of important files"""
        current_path = Path.cwd()
        backup_dir = current_path / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backed_up_files = []
        
        try:
            backup_dir.mkdir()
            
            # Find important files to backup
            important_extensions = ['.py', '.js', '.html', '.css', '.txt', '.md', '.json']
            files = [f for f in current_path.iterdir() 
                    if f.is_file() and f.suffix.lower() in important_extensions]
            
            for file_path in files:
                backup_path = backup_dir / file_path.name
                shutil.copy2(str(file_path), str(backup_path))
                backed_up_files.append({
                    'file': file_path.name,
                    'size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
                    'backup_path': str(backup_path)
                })
            
            return {
                'backup_count': len(backed_up_files),
                'backup_directory': str(backup_dir),
                'backed_up_files': backed_up_files,
                'summary': f"Backed up {len(backed_up_files)} important files"
            }
            
        except Exception as e:
            return {'error': f'Failed to backup files: {e}'}
    
    async def _compress_old_files(self) -> Dict:
        """Compress old files to save space"""
        current_path = Path.cwd()
        compressed_files = []
        
        try:
            import zipfile
            
            # Find old files (> 30 days)
            old_files = []
            cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days
            
            for file_path in current_path.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    old_files.append(file_path)
            
            if not old_files:
                return {'message': 'No old files found to compress'}
            
            # Create archive
            archive_name = f"old_files_{datetime.now().strftime('%Y%m%d')}.zip"
            archive_path = current_path / archive_name
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in old_files:
                    zipf.write(file_path, file_path.name)
                    compressed_files.append({
                        'file': file_path.name,
                        'size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
                        'age_days': int((time.time() - file_path.stat().st_mtime) / 86400)
                    })
            
            return {
                'compressed_count': len(compressed_files),
                'archive_name': archive_name,
                'archive_size_mb': round(archive_path.stat().st_size / (1024 * 1024), 2),
                'compressed_files': compressed_files,
                'summary': f"Compressed {len(compressed_files)} old files into {archive_name}"
            }
            
        except Exception as e:
            return {'error': f'Failed to compress old files: {e}'}


# Testing interface
if __name__ == "__main__":
    import logging
    
    # Mock security manager for testing
    class MockSecurityManager:
        def can_execute_task(self, task):
            return True
        
        def log_agent_activity(self, agent, action, details):
            print(f"AUDIT: {agent} - {action}")
        
        agent_permissions = {
            'file_management_agent': type('MockPermissions', (), {
                'system_commands': False,
                'file_write': True,
                'network_access': False,
                'process_control': False,
                'allowed_paths': {str(Path.home())},
                'forbidden_paths': set()
            })()
        }
    
    class MockTask:
        def __init__(self, command):
            self.task_id = "test_123"
            self.command = command
    
    async def test_file_agent():
        # Setup
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("FileManagementAgent")
        
        hardware_info = {
            'llm_config': {
                'agent_configs': {
                    'file_management_agent': {
                        'level': 'MEDIUM',
                        'model': 'rule-based',
                        'fallback_to_rules': True
                    }
                }
            }
        }
        
        security_manager = MockSecurityManager()
        agent = FileManagementAgent(hardware_info, security_manager, logger)
        
        print(f"Created file management agent: {agent}")
        print(f"Capabilities: {agent.get_capabilities()}")
        
        # Test organize downloads
        print("\n" + "="*50)
        print("Testing organize downloads...")
        task = MockTask("organize downloads")
        result = await agent.execute_task(task)
        print(f"Result: {result}")
        
        # Test find duplicates
        print("\n" + "="*50)
        print("Testing find duplicates...")
        task = MockTask("find duplicates")
        result = await agent.execute_task(task)
        print(f"Result: {result}")
        
        # Test cleanup suggestions
        print("\n" + "="*50)
        print("Testing cleanup suggestions...")
        task = MockTask("clean up")
        result = await agent.execute_task(task)
        print(f"Result: {result}")
        
        await agent.shutdown()
    
    # Run test
    asyncio.run(test_file_agent())