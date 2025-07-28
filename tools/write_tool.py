import os
from pathlib import Path
from typing import Dict, Any, Optional

from .base_tool import Tool
from .vfs import VirtualFileSystem


class WriteTool(Tool):
    """A tool to write content to a file using the virtual file system."""

    def __init__(self):
        self.vfs: Optional[VirtualFileSystem] = None

    def set_vfs(self, vfs: VirtualFileSystem):
        """Set the virtual file system for this tool."""
        self.vfs = vfs

    @property
    def name(self) -> str:
        return "Write"

    def execute(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file using the virtual file system.

        Args:
            path (str): Path to file to write.
            content (str): Content to write to file.

        Returns:
            Dictionary with success or error message.
        """
        if not self.vfs:
            return {"error": "Virtual file system not initialized"}
            
        try:
            # Use the VFS to write the file
            result = self.vfs.write_file(path, content)
            
            # If the result is a string starting with "Error:", it's an error message
            if result.startswith("Error:"):
                return {"error": result}
                
            # Return success message
            return {
                "result": result,
                "path": path,
                "current_directory": str(self.vfs.get_cwd())
            }
            
        except Exception as e:
            return {"error": f"Error writing to file: {str(e)}"}
