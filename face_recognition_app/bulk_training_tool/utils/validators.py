"""
Validation utilities for bulk training tool.
"""

import os
from typing import Tuple


def validate_path(path: str, must_exist: bool = False, must_be_dir: bool = False) -> Tuple[bool, str]:
    """
    Validate file system path.
    
    Args:
        path: Path to validate
        must_exist: Path must exist
        must_be_dir: Path must be a directory
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Path is empty"
    
    if must_exist and not os.path.exists(path):
        return False, f"Path does not exist: {path}"
    
    if must_be_dir and os.path.exists(path) and not os.path.isdir(path):
        return False, f"Path is not a directory: {path}"
    
    return True, ""
