import os
from pathlib import Path
from typing import Tuple, Union

# Use the current working directory as the base for all file operations
BASE_DIR = Path.cwd().resolve()

def sanitize_path(path: str) -> Tuple[Path, bool, str]:
    """
    Sanitizes a file path and checks if it's within the allowed directory.
    
    Args:
        path (str): The path to sanitize, relative to the current working directory.
        
    Returns:
        Tuple[Path, bool, str]: A tuple containing:
            - The resolved Path object
            - A boolean indicating if the path is valid (True) or not (False)
            - An error message if the path is invalid, or empty string if valid
    """
    try:
        # Sanitize path to prevent directory traversal
        safe_path_str = path.lstrip('/\\')
        target_path = BASE_DIR.joinpath(safe_path_str).resolve()
        
        # For security, don't allow going to parent directories of the starting directory
        if not (str(target_path) == str(BASE_DIR) or str(target_path).startswith(str(BASE_DIR) + os.sep)):
            return target_path, False, "Error: Attempted to access a path outside the allowed scope."
            
        return target_path, True, ""
    except Exception as e:
        return None, False, f"Error processing path: {e}"

def validate_file_path(path: str) -> Tuple[Path, bool, str]:
    """
    Validates that a path points to a valid file within the allowed directory.
    
    Args:
        path (str): The file path to validate, relative to the current working directory.
        
    Returns:
        Tuple[Path, bool, str]: A tuple containing:
            - The resolved Path object
            - A boolean indicating if the path is valid (True) or not (False)
            - An error message if the path is invalid, or empty string if valid
    """
    target_path, is_valid, error = sanitize_path(path)
    
    if not is_valid:
        return target_path, False, error
        
    if not target_path.is_file():
        return target_path, False, f"Error: '{path}' is not a valid file."
        
    return target_path, True, ""

def validate_directory_path(path: str) -> Tuple[Path, bool, str]:
    """
    Validates that a path points to a valid directory within the allowed directory.
    
    Args:
        path (str): The directory path to validate, relative to the current working directory.
        
    Returns:
        Tuple[Path, bool, str]: A tuple containing:
            - The resolved Path object
            - A boolean indicating if the path is valid (True) or not (False)
            - An error message if the path is invalid, or empty string if valid
    """
    target_path, is_valid, error = sanitize_path(path)
    
    if not is_valid:
        return target_path, False, error
        
    if not target_path.is_dir():
        return target_path, False, f"Error: '{path}' is not a valid directory."
        
    return target_path, True, ""
