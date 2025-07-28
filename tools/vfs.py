"""
Virtual File System for secure tool operations.

This module provides a virtual file system that maintains its own state
without affecting the actual process working directory. It ensures all
file operations are constrained to the allowed base directory.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union


class VirtualFileSystem:
    """
    A virtual file system that tracks its own current directory state
    and ensures operations are constrained to the allowed base directory.
    """
    
    def __init__(self, base_path: Union[str, Path]):
        """
        Initialize the virtual file system.
        
        Args:
            base_path: The base directory that constrains all operations.
                      All operations will be restricted to this directory and its subdirectories.
        """
        self.base_path = Path(base_path).resolve()
        self.current_path = self.base_path
    
    def get_cwd(self) -> Path:
        """Get the current working directory in the virtual file system."""
        return self.current_path
    
    def change_directory(self, path: str) -> str:
        """
        Change the current directory in the virtual file system.
        
        Args:
            path: The target directory path (absolute or relative)
            
        Returns:
            A string with the new current directory or an error message
        """
        try:
            # Handle special cases
            if path == ".":
                return str(self.current_path)
            elif path == "..":
                if self.current_path == self.base_path:
                    return f"Already at base directory: {self.current_path}"
                self.current_path = self.current_path.parent
                return str(self.current_path)
            
            # Handle relative and absolute paths
            if os.path.isabs(path):
                # Absolute path - must be within base_path
                new_path = Path(path).resolve()
            else:
                # Relative path
                new_path = (self.current_path / path).resolve()
            
            # Security check
            if not str(new_path).startswith(str(self.base_path)):
                return f"Error: Path '{path}' is outside the allowed directory"
            
            if not new_path.exists():
                return f"Error: Directory '{path}' does not exist"
            
            if not new_path.is_dir():
                return f"Error: '{path}' is not a directory"
            
            self.current_path = new_path
            return str(self.current_path)
        
        except Exception as e:
            return f"Error changing directory: {str(e)}"
    
    def list_directory(self, path: Optional[str] = None) -> Union[List[dict], str]:
        """
        List contents of a directory in the virtual file system.
        
        Args:
            path: Optional path to list. If None, lists the current directory.
            
        Returns:
            A list of dictionaries with file information or an error message
        """
        try:
            # Determine the target path
            if path is None:
                target_path = self.current_path
            elif os.path.isabs(path):
                target_path = Path(path).resolve()
            else:
                target_path = (self.current_path / path).resolve()
            
            # Security check
            if not str(target_path).startswith(str(self.base_path)):
                return f"Error: Path '{path}' is outside the allowed directory"
            
            if not target_path.exists():
                return f"Error: Path '{path}' does not exist"
            
            if not target_path.is_dir():
                return f"Error: '{path}' is not a directory"
            
            # List directory contents
            contents = []
            for item in target_path.iterdir():
                item_type = "directory" if item.is_dir() else "file"
                size = item.stat().st_size if item.is_file() else None
                contents.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.current_path)),
                    "type": item_type,
                    "size": size
                })
            
            return contents
        
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def make_directory(self, path: str, parents: bool = False) -> str:
        """
        Create a directory in the virtual file system.
        
        Args:
            path: The directory path to create (absolute or relative)
            parents: If True, create parent directories as needed
            
        Returns:
            A success or error message
        """
        try:
            # Determine the target path
            if os.path.isabs(path):
                target_path = Path(path).resolve()
            else:
                target_path = (self.current_path / path).resolve()
            
            # Security check
            if not str(target_path).startswith(str(self.base_path)):
                return f"Error: Path '{path}' is outside the allowed directory"
            
            # Create the directory
            if parents:
                target_path.mkdir(parents=True, exist_ok=True)
                return f"Created directory (with parents): {path}"
            else:
                if target_path.exists():
                    return f"Directory already exists: {path}"
                target_path.mkdir()
                return f"Created directory: {path}"
        
        except Exception as e:
            return f"Error creating directory: {str(e)}"
    
    def read_file(self, path: str) -> Union[str, bytes]:
        """
        Read a file in the virtual file system.
        
        Args:
            path: The file path to read (absolute or relative)
            
        Returns:
            The file contents or an error message
        """
        try:
            # Determine the target path
            if os.path.isabs(path):
                target_path = Path(path).resolve()
            else:
                target_path = (self.current_path / path).resolve()
            
            # Security check
            if not str(target_path).startswith(str(self.base_path)):
                return f"Error: Path '{path}' is outside the allowed directory"
            
            if not target_path.exists():
                return f"Error: File '{path}' does not exist"
            
            if not target_path.is_file():
                return f"Error: '{path}' is not a file"
            
            # Read the file
            return target_path.read_text()
        
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def write_file(self, path: str, content: str) -> str:
        """
        Write to a file in the virtual file system.
        
        Args:
            path: The file path to write to (absolute or relative)
            content: The content to write
            
        Returns:
            A success or error message
        """
        try:
            # Determine the target path
            if os.path.isabs(path):
                target_path = Path(path).resolve()
            else:
                target_path = (self.current_path / path).resolve()
            
            # Security check
            if not str(target_path).startswith(str(self.base_path)):
                return f"Error: Path '{path}' is outside the allowed directory"
            
            # Create parent directories if they don't exist
            if not target_path.parent.exists():
                target_path.parent.mkdir(parents=True)
            
            # Write to the file
            target_path.write_text(content)
            return f"Successfully wrote to file: {path}"
        
        except Exception as e:
            return f"Error writing to file: {str(e)}"
