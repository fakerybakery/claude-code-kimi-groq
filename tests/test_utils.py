"""
Tests for the utils module.

These tests focus on path sanitization and validation functions.
"""

import os
import pytest
from pathlib import Path
from tools.utils import sanitize_path, validate_file_path, validate_directory_path

class TestSanitizePath:
    """Tests for the sanitize_path function."""
    
    def test_normal_relative_path(self, tmp_path):
        """Test with normal relative paths."""
        # Setup
        os.chdir(tmp_path)
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = sanitize_path("test_dir")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_dir
    
    def test_absolute_path_within_base(self, tmp_path):
        """Test with absolute paths within BASE_DIR."""
        # Setup
        os.chdir(tmp_path)
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = sanitize_path(str(test_dir))
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_dir
    
    def test_path_traversal_attempt(self, tmp_path):
        """Test with path traversal attempts."""
        # Setup
        os.chdir(tmp_path)
        
        # Test
        path, is_valid, error = sanitize_path("../../../etc/passwd")
        
        # Verify
        assert not is_valid
        assert "outside the allowed scope" in error
    
    def test_malformed_path(self, tmp_path):
        """Test with malformed paths."""
        # Setup
        os.chdir(tmp_path)
        
        # Test
        path, is_valid, error = sanitize_path("///invalid///path///")
        
        # Verify - this should still be valid but normalized
        assert is_valid
        assert error == ""
        assert path == tmp_path / "invalid/path"
    
    def test_empty_path(self, tmp_path):
        """Test with empty string."""
        # Setup
        os.chdir(tmp_path)
        
        # Test
        path, is_valid, error = sanitize_path("")
        
        # Verify - empty path should resolve to current directory
        assert is_valid
        assert error == ""
        assert path == tmp_path
    
    def test_current_directory(self, tmp_path):
        """Test with current directory."""
        # Setup
        os.chdir(tmp_path)
        
        # Test
        path, is_valid, error = sanitize_path(".")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == tmp_path


class TestValidateFilePath:
    """Tests for the validate_file_path function."""
    
    def test_existing_file(self, tmp_path):
        """Test with existing file."""
        # Setup
        os.chdir(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        # Test
        path, is_valid, error = validate_file_path("test.txt")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_file
    
    def test_non_existent_file(self, tmp_path):
        """Test with non-existent file."""
        # Setup
        os.chdir(tmp_path)
        
        # Test
        path, is_valid, error = validate_file_path("non_existent.txt")
        
        # Verify
        assert not is_valid
        assert "is not a valid file" in error
    
    def test_directory_as_file(self, tmp_path):
        """Test with directory path when file expected."""
        # Setup
        os.chdir(tmp_path)
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = validate_file_path("test_dir")
        
        # Verify
        assert not is_valid
        assert "is not a valid file" in error
    
    def test_file_outside_base_dir(self, tmp_path):
        """Test with file path outside base directory."""
        # Setup
        os.chdir(tmp_path)
        
        # Test - assuming /etc/passwd exists on the system
        path, is_valid, error = validate_file_path("../../../etc/passwd")
        
        # Verify
        assert not is_valid
        assert "outside the allowed scope" in error


class TestValidateDirectoryPath:
    """Tests for the validate_directory_path function."""
    
    def test_existing_directory(self, tmp_path):
        """Test with existing directory."""
        # Setup
        os.chdir(tmp_path)
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Test
        path, is_valid, error = validate_directory_path("test_dir")
        
        # Verify
        assert is_valid
        assert error == ""
        assert path == test_dir
    
    def test_non_existent_directory(self, tmp_path):
        """Test with non-existent directory."""
        # Setup
        os.chdir(tmp_path)
        
        # Test
        path, is_valid, error = validate_directory_path("non_existent_dir")
        
        # Verify
        assert not is_valid
        assert "is not a valid directory" in error
    
    def test_file_as_directory(self, tmp_path):
        """Test with file path when directory expected."""
        # Setup
        os.chdir(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        # Test
        path, is_valid, error = validate_directory_path("test.txt")
        
        # Verify
        assert not is_valid
        assert "is not a valid directory" in error
    
    def test_directory_outside_base_dir(self, tmp_path):
        """Test with directory path outside base directory."""
        # Setup
        os.chdir(tmp_path)
        
        # Test - assuming /etc exists on the system
        path, is_valid, error = validate_directory_path("../../../etc")
        
        # Verify
        assert not is_valid
        assert "outside the allowed scope" in error
