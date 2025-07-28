"""
Tests for the Virtual File System (VFS) module.

These tests focus on secure directory and file operations within the VFS.
"""

import os
import pytest
from pathlib import Path
from tools.vfs import VirtualFileSystem

class TestVFSInitialization:
    """Tests for VirtualFileSystem initialization."""
    
    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        vfs = VirtualFileSystem(str(tmp_path))
        assert vfs.base_path == tmp_path
        assert vfs.current_path == tmp_path
    
    def test_init_with_path_object(self, tmp_path):
        """Test initialization with Path object."""
        vfs = VirtualFileSystem(tmp_path)
        assert vfs.base_path == tmp_path
        assert vfs.current_path == tmp_path


class TestVFSGetCWD:
    """Tests for VirtualFileSystem.get_cwd method."""
    
    def test_get_cwd(self, vfs, temp_vfs_dir):
        """Test getting current working directory."""
        assert vfs.get_cwd() == temp_vfs_dir


class TestVFSChangeDirectory:
    """Tests for VirtualFileSystem.change_directory method."""
    
    def test_change_to_subdirectory(self, vfs, temp_vfs_dir):
        """Test changing to subdirectory."""
        result = vfs.change_directory("test_dir")
        assert "Error" not in result
        assert vfs.get_cwd() == temp_vfs_dir / "test_dir"
    
    def test_change_to_parent_directory(self, vfs, temp_vfs_dir):
        """Test changing to parent directory."""
        # First change to a subdirectory
        vfs.change_directory("test_dir")
        
        # Then go back up
        result = vfs.change_directory("..")
        assert "Error" not in result
        assert vfs.get_cwd() == temp_vfs_dir
    
    def test_change_to_current_directory(self, vfs, temp_vfs_dir):
        """Test changing to current directory."""
        result = vfs.change_directory(".")
        assert "Error" not in result
        assert vfs.get_cwd() == temp_vfs_dir
    
    def test_change_with_absolute_path(self, vfs, temp_vfs_dir):
        """Test changing with absolute path."""
        test_dir_path = temp_vfs_dir / "test_dir"
        result = vfs.change_directory(str(test_dir_path))
        assert "Error" not in result
        assert vfs.get_cwd() == test_dir_path
    
    def test_directory_traversal_attempt(self, vfs):
        """Test directory traversal attempt."""
        result = vfs.change_directory("../../../etc")
        assert "Error" in result
        assert "outside the allowed directory" in result
    
    def test_non_existent_directory(self, vfs):
        """Test with non-existent directory."""
        result = vfs.change_directory("non_existent_dir")
        assert "Error" in result
        assert "does not exist" in result
    
    def test_file_as_directory(self, vfs):
        """Test with file path when directory expected."""
        result = vfs.change_directory("test.txt")
        assert "Error" in result
        assert "is not a directory" in result


class TestVFSListDirectory:
    """Tests for VirtualFileSystem.list_directory method."""
    
    def test_list_current_directory(self, vfs):
        """Test listing current directory."""
        contents = vfs.list_directory()
        assert isinstance(contents, list)
        
        # Check for expected files and directories
        names = [item["name"] for item in contents]
        assert "test.txt" in names
        assert "test_dir" in names
        assert ".hidden" in names
        assert ".hidden_dir" in names
    
    def test_list_specific_directory(self, vfs, temp_vfs_dir):
        """Test listing specific directory."""
        contents = vfs.list_directory("test_dir")
        assert isinstance(contents, list)
        
        # Check for expected files
        names = [item["name"] for item in contents]
        assert "nested.txt" in names
    
    def test_list_with_absolute_path(self, vfs, temp_vfs_dir):
        """Test listing with absolute path."""
        test_dir_path = temp_vfs_dir / "test_dir"
        contents = vfs.list_directory(str(test_dir_path))
        assert isinstance(contents, list)
        
        # Check for expected files
        names = [item["name"] for item in contents]
        assert "nested.txt" in names
    
    def test_list_non_existent_directory(self, vfs):
        """Test listing non-existent directory."""
        result = vfs.list_directory("non_existent_dir")
        assert isinstance(result, str)
        assert "Error" in result
        assert "does not exist" in result
    
    def test_list_file_as_directory(self, vfs):
        """Test listing file as directory."""
        result = vfs.list_directory("test.txt")
        assert isinstance(result, str)
        assert "Error" in result
        assert "is not a directory" in result
    
    def test_list_outside_base_directory(self, vfs):
        """Test listing outside base directory."""
        result = vfs.list_directory("../../../etc")
        assert isinstance(result, str)
        assert "Error" in result
        assert "outside the allowed directory" in result


class TestVFSMakeDirectory:
    """Tests for VirtualFileSystem.make_directory method."""
    
    def test_create_simple_directory(self, vfs, temp_vfs_dir):
        """Test creating simple directory."""
        result = vfs.make_directory("new_dir")
        assert "Error" not in result
        assert "Created directory" in result
        assert (temp_vfs_dir / "new_dir").exists()
        assert (temp_vfs_dir / "new_dir").is_dir()
    
    def test_create_nested_directory_with_parents(self, vfs, temp_vfs_dir):
        """Test creating nested directory with parents=True."""
        result = vfs.make_directory("nested/multi/level/dir", parents=True)
        assert "Error" not in result
        assert "Created directory (with parents)" in result
        assert (temp_vfs_dir / "nested/multi/level/dir").exists()
        assert (temp_vfs_dir / "nested/multi/level/dir").is_dir()
    
    def test_create_nested_directory_without_parents(self, vfs):
        """Test creating nested directory without parents=True."""
        result = vfs.make_directory("nested2/dir")
        assert "Error" in result
    
    def test_create_existing_directory(self, vfs):
        """Test creating existing directory."""
        result = vfs.make_directory("test_dir")
        assert "already exists" in result
    
    def test_create_directory_outside_base(self, vfs):
        """Test creating directory outside base directory."""
        result = vfs.make_directory("../../../tmp/test_escape")
        assert "Error" in result
        assert "outside the allowed directory" in result


class TestVFSReadFile:
    """Tests for VirtualFileSystem.read_file method."""
    
    def test_read_existing_file(self, vfs):
        """Test reading existing file."""
        content = vfs.read_file("test.txt")
        assert content == "This is a test file"
    
    def test_read_nested_file(self, vfs):
        """Test reading nested file."""
        content = vfs.read_file("test_dir/nested.txt")
        assert content == "This is a nested test file"
    
    def test_read_with_absolute_path(self, vfs, temp_vfs_dir):
        """Test reading with absolute path."""
        file_path = temp_vfs_dir / "test.txt"
        content = vfs.read_file(str(file_path))
        assert content == "This is a test file"
    
    def test_read_non_existent_file(self, vfs):
        """Test reading non-existent file."""
        result = vfs.read_file("non_existent.txt")
        assert "Error" in result
        assert "does not exist" in result
    
    def test_read_directory_as_file(self, vfs):
        """Test reading directory as file."""
        result = vfs.read_file("test_dir")
        assert "Error" in result
        assert "is not a file" in result
    
    def test_read_file_outside_base(self, vfs):
        """Test reading file outside base directory."""
        result = vfs.read_file("../../../etc/passwd")
        assert "Error" in result
        assert "outside the allowed directory" in result


class TestVFSWriteFile:
    """Tests for VirtualFileSystem.write_file method."""
    
    def test_write_new_file(self, vfs, temp_vfs_dir):
        """Test writing to new file."""
        result = vfs.write_file("new_file.txt", "New file content")
        assert "Error" not in result
        assert "Successfully wrote" in result
        
        # Verify file was created with correct content
        assert (temp_vfs_dir / "new_file.txt").exists()
        assert (temp_vfs_dir / "new_file.txt").read_text() == "New file content"
    
    def test_overwrite_existing_file(self, vfs, temp_vfs_dir):
        """Test overwriting existing file."""
        result = vfs.write_file("test.txt", "Updated content")
        assert "Error" not in result
        assert "Successfully wrote" in result
        
        # Verify file was updated
        assert (temp_vfs_dir / "test.txt").read_text() == "Updated content"
    
    def test_write_to_nested_path(self, vfs, temp_vfs_dir):
        """Test writing to nested path."""
        result = vfs.write_file("test_dir/new_nested.txt", "Nested content")
        assert "Error" not in result
        assert "Successfully wrote" in result
        
        # Verify file was created
        assert (temp_vfs_dir / "test_dir/new_nested.txt").exists()
        assert (temp_vfs_dir / "test_dir/new_nested.txt").read_text() == "Nested content"
    
    def test_write_with_absolute_path(self, vfs, temp_vfs_dir):
        """Test writing with absolute path."""
        file_path = temp_vfs_dir / "absolute_path.txt"
        result = vfs.write_file(str(file_path), "Absolute path content")
        assert "Error" not in result
        assert "Successfully wrote" in result
        
        # Verify file was created
        assert file_path.exists()
        assert file_path.read_text() == "Absolute path content"
    
    def test_write_file_outside_base(self, vfs):
        """Test writing file outside base directory."""
        result = vfs.write_file("../../../tmp/escape.txt", "Escape attempt")
        assert "Error" in result
        assert "outside the allowed directory" in result
    
    def test_write_to_directory_path(self, vfs):
        """Test writing to directory path."""
        result = vfs.write_file("test_dir", "This should fail")
        assert "Error" in result
