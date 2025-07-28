import os
from pathlib import Path
from typing import Union, Dict, Optional, Any

from .base_tool import Tool
from .vfs import VirtualFileSystem


class ReadTool(Tool):
    """A tool to read file contents using the virtual file system."""

    def __init__(self):
        self.vfs: Optional[VirtualFileSystem] = None

    def set_vfs(self, vfs: VirtualFileSystem):
        """Set the virtual file system for this tool."""
        self.vfs = vfs

    @property
    def name(self) -> str:
        return "Read"

    def execute(self, path: str) -> Dict[str, Any]:
        """Read contents of a file using the virtual file system.

        Args:
            path (str): Path to file to read.

        Returns:
            Dictionary with file contents or error message.
        """
        if not self.vfs:
            return {"error": "Virtual file system not initialized"}
            
        try:
            # Use the VFS to read the file
            content = self.vfs.read_file(path)
            
            # If the result is a string starting with "Error:", it's an error message
            if isinstance(content, str) and content.startswith("Error:"):
                return {"error": content}
                
            # Return the file contents
            return {
                "result": f"Contents of {path}:",
                "content": content,
                "current_directory": str(self.vfs.get_cwd())
            }
            
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}
