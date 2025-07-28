"""
Test configuration and fixtures for the Claude Code Kimi Groq proxy.
"""

import os
import pytest
from pathlib import Path
from tools.vfs import VirtualFileSystem
from tools.bash_tool import BashTool

@pytest.fixture
def temp_vfs_dir(tmp_path):
    """Create a temporary directory for VFS testing."""
    vfs_dir = tmp_path / "vfs_test"
    vfs_dir.mkdir()
    
    # Create some test files and directories
    test_file = vfs_dir / "test.txt"
    test_file.write_text("This is a test file")
    
    test_dir = vfs_dir / "test_dir"
    test_dir.mkdir()
    
    nested_file = test_dir / "nested.txt"
    nested_file.write_text("This is a nested test file")
    
    # Create a hidden file and directory
    hidden_file = vfs_dir / ".hidden"
    hidden_file.write_text("This is a hidden file")
    
    hidden_dir = vfs_dir / ".hidden_dir"
    hidden_dir.mkdir()
    
    return vfs_dir

@pytest.fixture
def vfs(temp_vfs_dir):
    """Create a VirtualFileSystem instance for testing."""
    return VirtualFileSystem(temp_vfs_dir)

@pytest.fixture
def bash_tool(vfs):
    """Create a BashTool instance with VFS for testing."""
    tool = BashTool()
    tool.set_vfs(vfs)
    return tool
