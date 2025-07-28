import os
from pathlib import Path
from typing import Dict, List, Union, Optional

from .base_tool import Tool
from .vfs import VirtualFileSystem


class LSTool(Tool):
    """A tool to list directory contents using the virtual file system."""

    def __init__(self):
        self.vfs: Optional[VirtualFileSystem] = None

    def set_vfs(self, vfs: VirtualFileSystem):
        """Set the virtual file system for this tool."""
        self.vfs = vfs

    @property
    def name(self) -> str:
        return "LS"

    def execute(self, path: str = ".") -> Union[Dict[str, Union[str, List[Dict]]], str]:
        """List contents of a directory using the virtual file system.

        Args:
            path (str): Path to directory to list. Defaults to current directory.

        Returns:
            Dictionary with results or error message.
        """
        if not self.vfs:
            return {"error": "Virtual file system not initialized"}
            
        try:
            # Use the VFS to list directory contents
            contents = self.vfs.list_directory(path)
            
            # If the result is a string, it's an error message
            if isinstance(contents, str):
                return {"error": contents}
                
            # Return formatted results
            return {
                "result": f"Contents of {path if path != '.' else self.vfs.get_cwd()}:",
                "items": contents,
                "current_directory": str(self.vfs.get_cwd())
            }
            
        except Exception as e:
            return {"error": f"Error listing directory: {str(e)}"}
