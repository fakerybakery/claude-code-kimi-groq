"""
Tests for the utils module.

These tests focus on path sanitization and validation functions.
"""

import os
import pytest
import sys
from pathlib import Path

# Import the module to be able to modify BASE_DIR for testing
import tools.utils
from tools.utils import sanitize_path, validate_file_path, validate_directory_path

@pytest.fixture
def with_tmp_base_dir(tmp_path):
    """Temporarily change BASE_DIR to tmp_path for testing."""
    original_base_dir = tools.utils.BASE_DIR
    tools.utils.BASE_DIR = tmp_path
    yield tmp_path
    tools.utils.BASE_DIR = original_base_dir


class TestSanitizePath:
    """Tests for the sanitize_path function."""
    
    def test_normal_relative_path(self, with_tmp_base_dir):
        """Test with normal relative paths."""
        # Setup
        tmp_path = with_tmp_base_dir
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = sanitize_path("test_dir")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_dir
    
    def test_absolute_path_within_base(self, with_tmp_base_dir):
        """Test with absolute paths within BASE_DIR."""
        # Setup
        tmp_path = with_tmp_base_dir
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = sanitize_path(str(test_dir))
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_dir
    
    def test_path_traversal_attempt(self, with_tmp_base_dir):
        """Test with path traversal attempts."""
        # Test
        path, is_valid, error = sanitize_path("../../../etc/passwd")
        
        # Verify
        assert not is_valid
        assert "outside the allowed scope" in error
    
    def test_malformed_path(self, with_tmp_base_dir):
        """Test with malformed paths."""
        # Setup
        tmp_path = with_tmp_base_dir
        
        # Test
        path, is_valid, error = sanitize_path("///invalid///path///")
        
        # Verify - this should still be valid but normalized
        assert is_valid
        assert error == ""
        assert path == tmp_path / "invalid/path"
    
    def test_empty_path(self, with_tmp_base_dir):
        """Test with empty string."""
        # Setup
        tmp_path = with_tmp_base_dir
        
        # Test
        path, is_valid, error = sanitize_path("")
        
        # Verify - empty path should resolve to current directory
        assert is_valid
        assert error == ""
        assert path == tmp_path
    
    def test_current_directory(self, with_tmp_base_dir):
        """Test with current directory."""
        # Setup
        tmp_path = with_tmp_base_dir
        
        # Test
        path, is_valid, error = sanitize_path(".")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == tmp_path


class TestValidateFilePath:
    """Tests for the validate_file_path function."""
    
    def test_existing_file(self, with_tmp_base_dir):
        """Test with existing file."""
        # Setup
        tmp_path = with_tmp_base_dir
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        # Test
        path, is_valid, error = validate_file_path("test.txt")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_file
    
    def test_non_existent_file(self, with_tmp_base_dir):
        """Test with non-existent file."""
        # Setup
        tmp_path = with_tmp_base_dir
        
        # Test
        path, is_valid, error = validate_file_path("non_existent.txt")
        
        # Verify
        assert not is_valid
        assert "is not a valid file" in error
    
    def test_directory_as_file(self, with_tmp_base_dir):
        """Test with directory path when file expected."""
        # Setup
        tmp_path = with_tmp_base_dir
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = validate_file_path("test_dir")
        
        # Verify
        assert not is_valid
        assert "is not a valid file" in error
    
    def test_file_outside_base_dir(self, with_tmp_base_dir):
        """Test with file path outside base directory."""
        # Test - assuming /etc/passwd exists on the system
        path, is_valid, error = validate_file_path("../../../etc/passwd")
        
        # Verify
        assert not is_valid
        assert "outside the allowed scope" in error


class TestValidateDirectoryPath:
    """Tests for the validate_directory_path function."""
    
    def test_existing_directory(self, with_tmp_base_dir):
        """Test with existing directory."""
        # Setup
        tmp_path = with_tmp_base_dir
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = validate_directory_path("test_dir")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_dir
    
    def test_non_existent_directory(self, with_tmp_base_dir):
        """Test with non-existent directory."""
        # Setup
        tmp_path = with_tmp_base_dir
        
        # Test
        path, is_valid, error = validate_directory_path("non_existent_dir")
        
        # Verify
        assert not is_valid
        assert "is not a valid directory" in error
    
    def test_file_as_directory(self, with_tmp_base_dir):
        """Test with file path when directory expected."""
        # Setup
        tmp_path = with_tmp_base_dir
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        # Test
        path, is_valid, error = validate_directory_path("test.txt")
        
        # Verify
        assert not is_valid
        assert "is not a valid directory" in error
    
    def test_directory_outside_base_dir(self, with_tmp_base_dir):
        """Test with directory path outside base directory."""
        # Test - assuming /etc exists on the system
        path, is_valid, error = validate_directory_path("../../../etc")
        
        # Verify
        assert not is_valid
        assert "outside the allowed scope" in error
