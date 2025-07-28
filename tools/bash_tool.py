import os
import re
import shlex
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base_tool import Tool
from .vfs import VirtualFileSystem

class BashTool(Tool):
    """A tool to execute simple, whitelisted shell commands in a secure virtual file system."""

    def __init__(self):
        self.vfs: Optional[VirtualFileSystem] = None
        # Define allowed commands and their handlers
        self.command_handlers = {
            'pwd': self._handle_pwd,
            'cd': self._handle_cd,
            'mkdir': self._handle_mkdir,
            'ls': self._handle_ls,
            'echo': self._handle_echo
        }

    def set_vfs(self, vfs: VirtualFileSystem):
        """Set the virtual file system for this tool."""
        self.vfs = vfs

    @property
    def name(self) -> str:
        return "Bash"

    def execute(self, command: str, description: str = "") -> Dict[str, Any]:
        """Executes a whitelisted shell command in the virtual file system.

        Args:
            command (str): The command to execute (e.g., 'pwd', 'cd dir', 'mkdir -p dir').
            description (str): An optional description of the command's purpose.

        Returns:
            Dict with result or error information.
        """
        if not self.vfs:
            return {"error": "Virtual file system not initialized"}

        # Check for command chaining
        if any(chain_op in command for chain_op in ['&&', '||', ';', '|', '`', '$(']):
            # Special case for mkdir && cd pattern that's commonly used
            if '&&' in command and 'mkdir' in command and 'cd' in command:
                parts = command.split('&&')
                if len(parts) == 2 and parts[0].strip().startswith('mkdir') and parts[1].strip().startswith('cd'):
                    # Extract directory name
                    mkdir_cmd = parts[0].strip()
                    cd_cmd = parts[1].strip()
                    
                    # Execute mkdir first
                    mkdir_result = self._parse_and_execute_command(mkdir_cmd)
                    if 'error' in mkdir_result:
                        return mkdir_result
                    
                    # Then execute cd
                    cd_result = self._parse_and_execute_command(cd_cmd)
                    return {
                        "result": f"{mkdir_result['result']}\n{cd_result['result']}",
                        "current_directory": str(self.vfs.get_cwd())
                    }
            return {"error": "Command chaining is not allowed for security reasons. Please use separate commands."}

        return self._parse_and_execute_command(command)

    def _parse_and_execute_command(self, command: str) -> Dict[str, Any]:
        """Parse and execute a single command."""
        try:
            # Use shlex to properly handle quoted arguments
            args = shlex.split(command)
            if not args:
                return {"error": "Empty command"}

            cmd = args[0].lower()
            if cmd not in self.command_handlers:
                allowed_cmds = ", ".join(self.command_handlers.keys())
                return {"error": f"Command '{cmd}' is not supported. Allowed commands: {allowed_cmds}"}

            # Call the appropriate handler
            return self.command_handlers[cmd](args[1:] if len(args) > 1 else [])

        except Exception as e:
            return {"error": f"Error parsing command: {str(e)}"}

    def _handle_pwd(self, args: List[str]) -> Dict[str, Any]:
        """Handle the pwd command."""
        try:
            return {"result": str(self.vfs.get_cwd()), "current_directory": str(self.vfs.get_cwd())}
        except Exception as e:
            return {"error": f"Error executing 'pwd': {str(e)}"}

    def _handle_cd(self, args: List[str]) -> Dict[str, Any]:
        """Handle the cd command."""
        try:
            if not args:
                # cd with no args goes to home/base directory
                result = self.vfs.change_directory(str(self.vfs.base_path))
            else:
                result = self.vfs.change_directory(args[0])
            
            return {"result": result, "current_directory": str(self.vfs.get_cwd())}
        except Exception as e:
            return {"error": f"Error executing 'cd': {str(e)}"}

    def _handle_mkdir(self, args: List[str]) -> Dict[str, Any]:
        """Handle the mkdir command."""
        try:
            if not args:
                return {"error": "mkdir: missing operand"}

            # Check for -p flag
            create_parents = False
            dir_paths = []

            for arg in args:
                if arg == "-p":
                    create_parents = True
                elif not arg.startswith("-"):
                    dir_paths.append(arg)

            if not dir_paths:
                return {"error": "mkdir: missing directory operand"}

            results = []
            for path in dir_paths:
                result = self.vfs.make_directory(path, parents=create_parents)
                results.append(result)

            return {"result": "\n".join(results), "current_directory": str(self.vfs.get_cwd())}
        except Exception as e:
            return {"error": f"Error executing 'mkdir': {str(e)}"}

    def _handle_ls(self, args: List[str]) -> Dict[str, Any]:
        """Handle the ls command."""
        try:
            # Simple ls implementation - can be expanded with flags like -l, -a, etc.
            path = None if not args else args[-1] if not args[-1].startswith('-') else None
            
            contents = self.vfs.list_directory(path)
            if isinstance(contents, str):  # Error message
                return {"error": contents}
            
            # Format the output
            formatted_items = []
            for item in contents:
                if item["type"] == "directory":
                    formatted_items.append(f"{item['name']}/")
                else:
                    formatted_items.append(item["name"])
            
            result = "  ".join(formatted_items) if formatted_items else "(empty directory)"
            return {"result": result, "items": contents, "current_directory": str(self.vfs.get_cwd())}
        except Exception as e:
            return {"error": f"Error executing 'ls': {str(e)}"}

    def _handle_echo(self, args: List[str]) -> Dict[str, Any]:
        """Handle the echo command."""
        try:
            return {"result": " ".join(args)}
        except Exception as e:
            return {"error": f"Error executing 'echo': {str(e)}"}
