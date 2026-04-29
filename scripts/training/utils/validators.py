"""
Validation utilities for URLs, paths, and configuration
"""

import os
import re
from typing import Tuple
from urllib.parse import urlparse


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL format (must start with http:// or https://).
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    if not url:
        return False, "URL cannot be empty"
    
    # Check if URL starts with http:// or https://
    if not url.startswith(('http://', 'https://')):
        return False, "URL must start with 'http://' or 'https://'"
    
    # Parse URL to validate structure
    try:
        parsed = urlparse(url)
        
        # Check if scheme and netloc are present
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        
        # Check for valid scheme
        if parsed.scheme not in ('http', 'https'):
            return False, "URL scheme must be 'http' or 'https'"
        
        return True, ""
    
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def validate_path(path: str, must_exist: bool = False, must_be_dir: bool = False) -> Tuple[bool, str]:
    """
    Validate file system path.
    
    Args:
        path: Path string to validate
        must_exist: If True, path must exist on file system
        must_be_dir: If True, path must be a directory
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    if not path:
        return False, "Path cannot be empty"
    
    # Check for invalid characters (basic check)
    # Allow alphanumeric, spaces, and common path characters
    if re.search(r'[<>"|?*]', path):
        return False, "Path contains invalid characters"
    
    # If must_exist is True, check if path exists
    if must_exist:
        if not os.path.exists(path):
            return False, f"Path does not exist: {path}"
        
        # If must_be_dir is True, check if it's a directory
        if must_be_dir and not os.path.isdir(path):
            return False, f"Path is not a directory: {path}"
    
    return True, ""


def validate_database_url(database_url: str) -> Tuple[bool, str]:
    """
    Validate PostgreSQL database URL format.
    
    Expected format: postgresql://user:password@host:port/database
    
    Args:
        database_url: Database connection string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not database_url:
        return False, "Database URL cannot be empty"
    
    # Check if URL starts with postgresql://
    if not database_url.startswith('postgresql://'):
        return False, "Database URL must start with 'postgresql://'"
    
    try:
        parsed = urlparse(database_url)
        
        # Check required components
        if not parsed.hostname:
            return False, "Database URL missing hostname"
        
        if not parsed.path or parsed.path == '/':
            return False, "Database URL missing database name"
        
        return True, ""
    
    except Exception as e:
        return False, f"Invalid database URL: {str(e)}"


def normalize_path(path: str) -> str:
    """
    Normalize file system path (resolve relative paths, remove trailing slashes).
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized absolute path
    """
    # Expand user home directory (~)
    path = os.path.expanduser(path)
    
    # Convert to absolute path
    path = os.path.abspath(path)
    
    # Normalize path separators
    path = os.path.normpath(path)
    
    return path
