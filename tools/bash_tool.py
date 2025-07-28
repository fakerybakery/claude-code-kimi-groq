import os
import re
import shlex
import time
import resource
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple

from .base_tool import Tool
from .vfs import VirtualFileSystem

class CommandSandbox:
    """Provides sandboxing for command execution with resource limits."""
    
    # Default resource limits
    DEFAULT_LIMITS = {
        "CPU_TIME": 5,  # 5 seconds of CPU time
        "MEMORY": 50 * 1024 * 1024,  # 50MB of memory
        "FILE_SIZE": 5 * 1024 * 1024,  # 5MB max file size
        "SUBPROCESS": 0,  # No subprocesses allowed
    }
    
    def __init__(self, limits: Dict[str, int] = None):
        """Initialize the sandbox with resource limits.
        
        Args:
            limits: Dictionary of resource limits to override defaults
        """
        self.limits = self.DEFAULT_LIMITS.copy()
        if limits:
            self.limits.update(limits)
    
    def set_resource_limits(self):
        """Set resource limits for the current process."""
        # Set CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (self.limits["CPU_TIME"], self.limits["CPU_TIME"]))
        
        # Set memory limit
        resource.setrlimit(resource.RLIMIT_AS, (self.limits["MEMORY"], self.limits["MEMORY"]))
        
        # Set file size limit
        resource.setrlimit(resource.RLIMIT_FSIZE, (self.limits["FILE_SIZE"], self.limits["FILE_SIZE"]))
        
        # Set subprocess limit (0 = no subprocesses)
        resource.setrlimit(resource.RLIMIT_NPROC, (self.limits["SUBPROCESS"], self.limits["SUBPROCESS"]))


class BashTool(Tool):
    """A tool to execute simple, whitelisted shell commands in a secure virtual file system."""

    # Regular expressions for detecting potentially dangerous patterns
    DANGEROUS_PATTERNS = [
        r'\$\(.*\)',  # Command substitution $(command)
        r'`.*`',       # Backtick command substitution
        r'>[^;]*',     # Output redirection
        r'<[^;]*',     # Input redirection
        r'\|[^;]*',    # Pipe
        r'&[^&]',      # Background execution
        r'\\[rn]',     # Escape sequences
        r'\\x[0-9a-fA-F]{2}',  # Hex escape sequences
        r'eval\s',     # eval command
        r'exec\s',     # exec command
        r'source\s',   # source command
        r'\. ',        # . command (source)
    ]

    def __init__(self):
        self.vfs: Optional[VirtualFileSystem] = None
        
        # Define allowed commands and their handlers
        self.command_handlers = {
            'pwd': self._handle_pwd,
            'cd': self._handle_cd,
            'mkdir': self._handle_mkdir,
            'ls': self._handle_ls
        }
        
        # Initialize command sandbox
        self.sandbox = CommandSandbox()
        
        # Track command execution for rate limiting
        self.command_history = []
        self.max_commands_per_minute = 30
        
        # Set of disallowed arguments
        self.disallowed_args: Set[str] = {
            '--help', '--version', '-v', '-h',  # Help/version flags that might reveal system info
            '-r', '-f', '--force',  # Force flags that might override safety checks
            '/etc', '/var', '/usr', '/bin', '/sbin',  # System directories
            '/dev', '/proc', '/sys',  # Special system directories
            '/root', '/home',  # User directories
            '~', '$HOME'  # Home directory references
        }

    def set_vfs(self, vfs: VirtualFileSystem):
        """Set the virtual file system for this tool."""
        self.vfs = vfs

    @property
    def name(self) -> str:
        return "Bash"
    
    def _check_rate_limit(self) -> Tuple[bool, str]:
        """Check if command execution is within rate limits.
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        current_time = time.time()
        # Remove commands older than 60 seconds
        self.command_history = [t for t in self.command_history if current_time - t < 60]
        
        # Check if we've exceeded the rate limit
        if len(self.command_history) >= self.max_commands_per_minute:
            return False, f"Rate limit exceeded: maximum {self.max_commands_per_minute} commands per minute"
        
        # Add current command to history
        self.command_history.append(current_time)
        return True, ""

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
        
        # Check rate limiting
        is_allowed, error_message = self._check_rate_limit()
        if not is_allowed:
            return {"error": error_message}

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return {"error": f"Command contains potentially dangerous pattern: {pattern}"}

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
            
            # Check for disallowed arguments
            for arg in args[1:]:
                for disallowed in self.disallowed_args:
                    if arg == disallowed or arg.startswith(disallowed + '/'):
                        return {"error": f"Argument '{arg}' is not allowed for security reasons"}

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
                else:
                    return {"error": f"mkdir: unsupported option: {arg}"}

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
            # Parse flags and path
            show_hidden = False
            long_format = False
            path = None
            
            for arg in args:
                if arg.startswith('-'):
                    if 'a' in arg:
                        show_hidden = True
                    if 'l' in arg:
                        long_format = True
                    # Ignore other flags for now
                else:
                    path = arg
            
            contents = self.vfs.list_directory(path)
            if isinstance(contents, str):  # Error message
                return {"error": contents}
            
            # Filter hidden files if not showing them
            if not show_hidden:
                contents = [item for item in contents if not item["name"].startswith('.')]
            
            # Format the output
            if long_format:
                formatted_items = []
                for item in contents:
                    type_char = 'd' if item["type"] == "directory" else '-'
                    size = item.get("size", 0) or 0
                    formatted_items.append(f"{type_char}rw-r--r--  1 user user {size:8d} Jul 28 12:00 {item['name']}")
                result = "\n".join(formatted_items) if formatted_items else "(empty directory)"
            else:
                formatted_items = []
                for item in contents:
                    if item["type"] == "directory":
                        formatted_items.append(f"{item['name']}/")
                    else:
                        formatted_items.append(item["name"])
                result = "  ".join(formatted_items) if formatted_items else "(empty directory)"
            
            return {
                "result": result, 
                "items": contents, 
                "current_directory": str(self.vfs.get_cwd()),
                "format": "long" if long_format else "short",
                "show_hidden": show_hidden
            }
        except Exception as e:
            return {"error": f"Error executing 'ls': {str(e)}"}

    # Echo, cat, and touch commands have been removed as they were not authorized
