"""
Text Editors Integration Client

Provides functionality to interact with various text editors for file editing
and text processing operations.
"""

import os
import subprocess
import tempfile
import json
import shutil
from typing import Dict, List, Optional, Any, Union
import logging
import platform

logger = logging.getLogger(__name__)

class TextEditorClient:
    """Client for interacting with various text editors"""
    
    def __init__(self):
        """Initialize text editor client"""
        self.system = platform.system().lower()
        self.available_editors = self._detect_available_editors()
        self.editor_paths = self._get_editor_paths()
    
    def _detect_available_editors(self) -> List[str]:
        """Detect available text editors on the system"""
        available = []
        
        # Common editors to check
        editors = ['nano', 'vim', 'emacs', 'notepad++', 'notepad', 'code', 'subl']
        
        for editor in editors:
            if self._is_editor_available(editor):
                available.append(editor)
        
        return available
    
    def _is_editor_available(self, editor: str) -> bool:
        """Check if a specific editor is available"""
        try:
            if editor == 'notepad++':
                # Check for Notepad++ on Windows
                if self.system == 'windows':
                    possible_paths = [
                        r'C:\Program Files\Notepad++\notepad++.exe',
                        r'C:\Program Files (x86)\Notepad++\notepad++.exe',
                        'notepad++'
                    ]
                    for path in possible_paths:
                        if shutil.which(path) or os.path.exists(path):
                            return True
                return False
            elif editor == 'notepad':
                # Check for Notepad on Windows
                if self.system == 'windows':
                    return shutil.which('notepad') is not None
                return False
            else:
                # Check for other editors
                return shutil.which(editor) is not None
        except Exception:
            return False
    
    def _get_editor_paths(self) -> Dict[str, str]:
        """Get paths to available editors"""
        paths = {}
        
        for editor in self.available_editors:
            if editor == 'notepad++':
                if self.system == 'windows':
                    possible_paths = [
                        r'C:\Program Files\Notepad++\notepad++.exe',
                        r'C:\Program Files (x86)\Notepad++\notepad++.exe',
                    ]
                    for path in possible_paths:
                        if os.path.exists(path):
                            paths[editor] = path
                            break
                    if editor not in paths:
                        paths[editor] = 'notepad++'
            else:
                paths[editor] = shutil.which(editor) or editor
        
        return paths
    
    def get_available_editors(self) -> List[str]:
        """Get list of available editors"""
        return self.available_editors
    
    def open_file(self, file_path: str, editor: str = "nano", 
                  line_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Open a file with specified editor
        
        Args:
            file_path: Path to file to open
            editor: Editor to use
            line_number: Optional line number to jump to
            
        Returns:
            Dictionary containing operation results
        """
        if editor not in self.available_editors:
            return {
                'success': False,
                'error': f'Editor {editor} not available'
            }
        
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': f'File not found: {file_path}'
            }
        
        try:
            editor_path = self.editor_paths[editor]
            cmd = [editor_path, file_path]
            
            # Add line number if specified
            if line_number and editor in ['vim', 'emacs', 'code', 'subl']:
                if editor == 'vim':
                    cmd.extend(['+', str(line_number)])
                elif editor == 'emacs':
                    cmd.extend(['+', str(line_number)])
                elif editor == 'code':
                    cmd.extend(['--goto', f'{file_path}:{line_number}'])
                elif editor == 'subl':
                    cmd.extend([f'{file_path}:{line_number}'])
            
            # Launch editor
            if editor in ['nano', 'vim', 'emacs']:
                # Terminal-based editors
                subprocess.Popen(cmd)
            else:
                # GUI editors
                subprocess.Popen(cmd, shell=True)
            
            return {
                'success': True,
                'message': f'Opened {file_path} with {editor}',
                'editor': editor,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error opening file with {editor}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_temp_file(self, content: str = "", 
                        suffix: str = ".txt",
                        editor: str = "nano") -> Dict[str, Any]:
        """
        Create a temporary file and open it with specified editor
        
        Args:
            content: Initial content for the file
            suffix: File suffix
            editor: Editor to use
            
        Returns:
            Dictionary containing operation results
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
                f.write(content)
                temp_file = f.name
            
            # Open with editor
            result = self.open_file(temp_file, editor)
            
            if result['success']:
                result['temp_file'] = temp_file
                result['message'] = f'Created temporary file and opened with {editor}'
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating temporary file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def edit_file_content(self, file_path: str, 
                         new_content: str,
                         backup: bool = True) -> Dict[str, Any]:
        """
        Edit file content programmatically
        
        Args:
            file_path: Path to file to edit
            new_content: New content for the file
            backup: Whether to create a backup
            
        Returns:
            Dictionary containing operation results
        """
        try:
            # Create backup if requested
            if backup and os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                'success': True,
                'message': f'File {file_path} updated successfully',
                'file_path': file_path,
                'backup_created': backup and os.path.exists(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error editing file content: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def read_file_content(self, file_path: str) -> Dict[str, Any]:
        """
        Read file content
        
        Args:
            file_path: Path to file to read
            
        Returns:
            Dictionary containing file content and metadata
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get file metadata
            stat = os.stat(file_path)
            
            return {
                'success': True,
                'content': content,
                'file_path': file_path,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'lines': len(content.splitlines())
            }
            
        except Exception as e:
            logger.error(f"Error reading file content: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_in_file(self, file_path: str, 
                      search_term: str,
                      case_sensitive: bool = False) -> Dict[str, Any]:
        """
        Search for text in a file
        
        Args:
            file_path: Path to file to search
            search_term: Text to search for
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            Dictionary containing search results
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            matches = []
            for line_num, line in enumerate(lines, 1):
                search_line = line if case_sensitive else line.lower()
                search_term_lower = search_term if case_sensitive else search_term.lower()
                
                if search_term_lower in search_line:
                    matches.append({
                        'line_number': line_num,
                        'line_content': line.rstrip(),
                        'column': search_line.find(search_term_lower) + 1
                    })
            
            return {
                'success': True,
                'matches': matches,
                'total_matches': len(matches),
                'search_term': search_term,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error searching in file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def replace_in_file(self, file_path: str,
                       search_term: str,
                       replace_term: str,
                       case_sensitive: bool = False,
                       backup: bool = True) -> Dict[str, Any]:
        """
        Replace text in a file
        
        Args:
            file_path: Path to file to edit
            search_term: Text to search for
            replace_term: Text to replace with
            case_sensitive: Whether search should be case sensitive
            backup: Whether to create a backup
            
        Returns:
            Dictionary containing operation results
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            # Create backup if requested
            if backup:
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Perform replacement
            if case_sensitive:
                new_content = content.replace(search_term, replace_term)
            else:
                # Case-insensitive replacement
                import re
                pattern = re.escape(search_term)
                new_content = re.sub(pattern, replace_term, content, flags=re.IGNORECASE)
            
            # Count replacements
            replacements = content.count(search_term) if case_sensitive else len(re.findall(re.escape(search_term), content, re.IGNORECASE))
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                'success': True,
                'message': f'Replaced {replacements} occurrences in {file_path}',
                'file_path': file_path,
                'replacements': replacements,
                'backup_created': backup
            }
            
        except Exception as e:
            logger.error(f"Error replacing in file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed information about a file
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary containing file information
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            stat = os.stat(file_path)
            
            # Read first few lines for preview
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            preview_lines = lines[:10]  # First 10 lines
            preview = ''.join(preview_lines)
            
            return {
                'success': True,
                'file_path': file_path,
                'size': stat.st_size,
                'size_human': self._format_file_size(stat.st_size),
                'modified': stat.st_mtime,
                'lines': len(lines),
                'encoding': 'utf-8',
                'preview': preview,
                'is_text': self._is_text_file(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _is_text_file(self, file_path: str) -> bool:
        """Check if file is a text file"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' not in chunk
        except Exception:
            return False
    
    def get_editor_info(self, editor: str) -> Dict[str, Any]:
        """
        Get information about a specific editor
        
        Args:
            editor: Editor name
            
        Returns:
            Dictionary containing editor information
        """
        if editor not in self.available_editors:
            return {
                'success': False,
                'error': f'Editor {editor} not available'
            }
        
        editor_info = {
            'nano': {
                'name': 'GNU nano',
                'type': 'terminal',
                'description': 'Simple terminal-based text editor',
                'features': ['syntax highlighting', 'search and replace', 'multiple buffers']
            },
            'vim': {
                'name': 'Vim',
                'type': 'terminal',
                'description': 'Powerful terminal-based text editor',
                'features': ['modal editing', 'extensive customization', 'powerful scripting']
            },
            'emacs': {
                'name': 'GNU Emacs',
                'type': 'terminal',
                'description': 'Extensible text editor and application framework',
                'features': ['Lisp-based extension', 'integrated development environment', 'powerful macros']
            },
            'notepad++': {
                'name': 'Notepad++',
                'type': 'gui',
                'description': 'Free source code editor for Windows',
                'features': ['syntax highlighting', 'plugin system', 'multi-document interface']
            },
            'notepad': {
                'name': 'Notepad',
                'type': 'gui',
                'description': 'Simple text editor included with Windows',
                'features': ['basic text editing', 'find and replace', 'word wrap']
            },
            'code': {
                'name': 'Visual Studio Code',
                'type': 'gui',
                'description': 'Free source code editor by Microsoft',
                'features': ['IntelliSense', 'debugging', 'git integration', 'extensions']
            },
            'subl': {
                'name': 'Sublime Text',
                'type': 'gui',
                'description': 'Sophisticated text editor for code and prose',
                'features': ['multiple selections', 'command palette', 'powerful API']
            }
        }
        
        info = editor_info.get(editor, {})
        info['path'] = self.editor_paths.get(editor, '')
        info['available'] = True
        
        return {
            'success': True,
            'editor': editor,
            'info': info
        }
