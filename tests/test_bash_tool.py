"""
Tests for the BashTool module.

These tests focus on secure command execution, command parsing,
and security restrictions in the BashTool.
"""

import os
import re
import time
import pytest
from pathlib import Path
from tools.bash_tool import BashTool, CommandSandbox


class TestCommandSandbox:
    """Tests for the CommandSandbox class."""
    
    def test_init_default_limits(self):
        """Test initialization with default limits."""
        sandbox = CommandSandbox()
        assert sandbox.limits["CPU_TIME"] == 5
        assert sandbox.limits["MEMORY"] == 50 * 1024 * 1024
        assert sandbox.limits["FILE_SIZE"] == 5 * 1024 * 1024
        assert sandbox.limits["SUBPROCESS"] == 0
    
    def test_init_custom_limits(self):
        """Test initialization with custom limits."""
        custom_limits = {
            "CPU_TIME": 10,
            "MEMORY": 100 * 1024 * 1024
        }
        sandbox = CommandSandbox(limits=custom_limits)
        assert sandbox.limits["CPU_TIME"] == 10
        assert sandbox.limits["MEMORY"] == 100 * 1024 * 1024
        assert sandbox.limits["FILE_SIZE"] == 5 * 1024 * 1024  # Default value
        assert sandbox.limits["SUBPROCESS"] == 0  # Default value


class TestBashToolInitialization:
    """Tests for BashTool initialization."""
    
    def test_init(self):
        """Test BashTool initialization."""
        tool = BashTool()
        assert tool.vfs is None
        assert tool.command_handlers is not None
        assert 'pwd' in tool.command_handlers
        assert 'cd' in tool.command_handlers
        assert 'mkdir' in tool.command_handlers
        assert 'ls' in tool.command_handlers
        assert tool.command_history == []
        assert tool.max_commands_per_minute == 30
    
    def test_set_vfs(self, vfs):
        """Test setting VFS."""
        tool = BashTool()
        tool.set_vfs(vfs)
        assert tool.vfs == vfs
    
    def test_name_property(self):
        """Test name property."""
        tool = BashTool()
        assert tool.name == "Bash"


class TestBashToolRateLimiting:
    """Tests for BashTool rate limiting."""
    
    def test_rate_limit_not_exceeded(self):
        """Test rate limit not exceeded."""
        tool = BashTool()
        is_allowed, error = tool._check_rate_limit()
        assert is_allowed
        assert error == ""
    
    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        tool = BashTool()
        # Add enough commands to exceed rate limit
        current_time = time.time()
        tool.command_history = [current_time] * 31
        
        is_allowed, error = tool._check_rate_limit()
        assert not is_allowed
        assert "Rate limit exceeded" in error


class TestBashToolSecurityPatterns:
    """Tests for BashTool security pattern detection."""
    
    @pytest.mark.parametrize("dangerous_command", [
        "$(ls)",
        "`ls`",
        "ls > file.txt",
        "ls < file.txt",
        "ls | grep test",
        "ls &",
        "eval ls",
        "exec ls",
        "source .bashrc",
        ". .bashrc",
    ])
    def test_dangerous_pattern_detection(self, bash_tool, dangerous_command):
        """Test detection of dangerous patterns in commands."""
        result = bash_tool.execute(dangerous_command)
        assert "error" in result
        assert "Security violation" in result["error"]


class TestBashToolCommandParsing:
    """Tests for BashTool command parsing."""
    
    def test_parse_simple_command(self, bash_tool):
        """Test parsing simple command."""
        result = bash_tool._parse_and_execute_command("pwd")
        assert "error" not in result
        assert "result" in result
    
    def test_parse_command_with_args(self, bash_tool):
        """Test parsing command with arguments."""
        result = bash_tool._parse_and_execute_command("mkdir test_dir")
        assert "error" not in result
        assert "result" in result
    
    def test_parse_unsupported_command(self, bash_tool):
        """Test parsing unsupported command."""
        result = bash_tool._parse_and_execute_command("unsupported_command")
        assert "error" in result
        assert "Unsupported command" in result["error"]
    
    def test_parse_command_with_disallowed_args(self, bash_tool):
        """Test parsing command with disallowed arguments."""
        result = bash_tool._parse_and_execute_command("cd /etc")
        assert "error" in result
        assert "Security violation" in result["error"]
    
    def test_parse_mkdir_cd_chain(self, bash_tool):
        """Test parsing mkdir && cd chain."""
        result = bash_tool.execute("mkdir test_chain && cd test_chain")
        assert "error" not in result
        assert "result" in result
        assert "Created directory" in result["result"]
        assert bash_tool.vfs.get_cwd().name == "test_chain"
    
    def test_parse_disallowed_chain(self, bash_tool):
        """Test parsing disallowed command chain."""
        result = bash_tool.execute("pwd && ls")
        assert "error" in result
        assert "Command chaining" in result["error"]


class TestBashToolCommandHandlers:
    """Tests for BashTool command handlers."""
    
    def test_handle_pwd(self, bash_tool, temp_vfs_dir):
        """Test pwd command handler."""
        result = bash_tool._handle_pwd([])
        assert "error" not in result
        assert "result" in result
        assert result["result"] == str(temp_vfs_dir)
        assert result["current_directory"] == str(temp_vfs_dir)
    
    def test_handle_cd_no_args(self, bash_tool, temp_vfs_dir):
        """Test cd command handler with no arguments."""
        # First change to a subdirectory
        bash_tool.vfs.change_directory("test_dir")
        
        # Then test cd with no args (should go to base directory)
        result = bash_tool._handle_cd([])
        assert "error" not in result
        assert "result" in result
        assert result["current_directory"] == str(temp_vfs_dir)
    
    def test_handle_cd_with_arg(self, bash_tool, temp_vfs_dir):
        """Test cd command handler with argument."""
        result = bash_tool._handle_cd(["test_dir"])
        assert "error" not in result
        assert "result" in result
        assert result["current_directory"] == str(temp_vfs_dir / "test_dir")
    
    def test_handle_mkdir_no_args(self, bash_tool):
        """Test mkdir command handler with no arguments."""
        result = bash_tool._handle_mkdir([])
        assert "error" in result
        assert "missing operand" in result["error"]
    
    def test_handle_mkdir_simple(self, bash_tool, temp_vfs_dir):
        """Test mkdir command handler with simple directory."""
        result = bash_tool._handle_mkdir(["new_test_dir"])
        assert "error" not in result
        assert "result" in result
        assert "Created directory" in result["result"]
        assert (temp_vfs_dir / "new_test_dir").exists()
    
    def test_handle_mkdir_with_p_flag(self, bash_tool, temp_vfs_dir):
        """Test mkdir command handler with -p flag."""
        result = bash_tool._handle_mkdir(["-p", "nested/test/dir"])
        assert "error" not in result
        assert "result" in result
        assert "Created directory" in result["result"]
        assert (temp_vfs_dir / "nested/test/dir").exists()
    
    def test_handle_mkdir_unsupported_option(self, bash_tool):
        """Test mkdir command handler with unsupported option."""
        result = bash_tool._handle_mkdir(["-z", "test_dir"])
        assert "error" in result
        assert "unsupported option" in result["error"]
    
    def test_handle_ls_no_args(self, bash_tool):
        """Test ls command handler with no arguments."""
        result = bash_tool._handle_ls([])
        assert "error" not in result
        assert "result" in result
        assert "items" in result
        assert isinstance(result["items"], list)
        
        # Check that test.txt and test_dir are in the results
        names = [item["name"] for item in result["items"]]
        assert "test.txt" in names
        assert "test_dir" in names
    
    def test_handle_ls_with_path(self, bash_tool):
        """Test ls command handler with path argument."""
        result = bash_tool._handle_ls(["test_dir"])
        assert "error" not in result
        assert "result" in result
        assert "items" in result
        
        # Check that nested.txt is in the results
        names = [item["name"] for item in result["items"]]
        assert "nested.txt" in names
    
    def test_handle_ls_with_a_flag(self, bash_tool):
        """Test ls command handler with -a flag."""
        result = bash_tool._handle_ls(["-a"])
        assert "error" not in result
        assert "result" in result
        assert "items" in result
        assert result["show_hidden"] is True
        
        # Check that hidden files are in the results
        names = [item["name"] for item in result["items"]]
        assert ".hidden" in names
        assert ".hidden_dir" in names
    
    def test_handle_ls_with_l_flag(self, bash_tool):
        """Test ls command handler with -l flag."""
        result = bash_tool._handle_ls(["-l"])
        assert "error" not in result
        assert "result" in result
        assert "format" in result
        assert result["format"] == "long"
        
        # Check that the result is formatted as expected
        assert "rw-r--r--" in result["result"]


class TestBashToolIntegration:
    """Integration tests for BashTool with VFS."""
    
    def test_command_sequence(self, bash_tool, temp_vfs_dir):
        """Test sequence of commands."""
        # Make a new directory
        result1 = bash_tool.execute("mkdir test_sequence")
        assert "error" not in result1
        
        # Change to that directory
        result2 = bash_tool.execute("cd test_sequence")
        assert "error" not in result2
        assert bash_tool.vfs.get_cwd() == temp_vfs_dir / "test_sequence"
        
        # Create a subdirectory
        result3 = bash_tool.execute("mkdir -p nested/dir")
        assert "error" not in result3
        assert (temp_vfs_dir / "test_sequence/nested/dir").exists()
        
        # List the directory
        result4 = bash_tool.execute("ls")
        assert "error" not in result4
        assert "nested" in result4["result"]
        
        # Go back to parent
        result5 = bash_tool.execute("cd ..")
        assert "error" not in result5
        assert bash_tool.vfs.get_cwd() == temp_vfs_dir
