"""Configuration data model for the face recognition application.

This module defines the AppConfig dataclass that holds all configuration
parameters for the Python real-time face recognition application.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """Application configuration with default values.
    
    Attributes:
        api_base_url: Base URL for the Flask API backend
        camera_index: Camera device index (0 for default camera)
        camera_width: Camera frame width in pixels
        camera_height: Camera frame height in pixels
        api_timeout: HTTP request timeout in seconds
        max_fps: Maximum frames per second to process
        display_window_name: Name of the display window
        jpeg_quality: JPEG compression quality (0-100)
    """
    api_base_url: str = "http://localhost:5000"
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    api_timeout: int = 5
    max_fps: int = 30
    display_window_name: str = "Face Recognition"
    jpeg_quality: int = 85


def load_config(config_file: Optional[str] = "config.json") -> AppConfig:
    """Load configuration from environment variables, config file, and defaults.
    
    Configuration priority (highest to lowest):
    1. Environment variables
    2. config.json file (if present)
    3. Default values
    
    Environment variable mapping:
    - FACE_API_URL → api_base_url
    - CAMERA_INDEX → camera_index
    - CAMERA_WIDTH → camera_width
    - CAMERA_HEIGHT → camera_height
    
    Args:
        config_file: Path to JSON configuration file (default: "config.json")
    
    Returns:
        AppConfig instance with merged configuration
    """
    # Start with default values
    config = AppConfig()
    
    # Load from config file if present (medium priority)
    if config_file and Path(config_file).exists():
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                
            # Update config with values from file
            if 'api_base_url' in file_config:
                config.api_base_url = file_config['api_base_url']
            if 'camera_index' in file_config:
                config.camera_index = int(file_config['camera_index'])
            if 'camera_width' in file_config:
                config.camera_width = int(file_config['camera_width'])
            if 'camera_height' in file_config:
                config.camera_height = int(file_config['camera_height'])
            if 'api_timeout' in file_config:
                config.api_timeout = int(file_config['api_timeout'])
            if 'max_fps' in file_config:
                config.max_fps = int(file_config['max_fps'])
            if 'display_window_name' in file_config:
                config.display_window_name = file_config['display_window_name']
            if 'jpeg_quality' in file_config:
                config.jpeg_quality = int(file_config['jpeg_quality'])
                
        except (json.JSONDecodeError, ValueError) as e:
            # Log warning but continue with defaults
            print(f"Warning: Failed to parse config file '{config_file}': {e}")
    
    # Load from environment variables (highest priority)
    if 'FACE_API_URL' in os.environ:
        config.api_base_url = os.environ['FACE_API_URL']
    
    if 'CAMERA_INDEX' in os.environ:
        try:
            config.camera_index = int(os.environ['CAMERA_INDEX'])
        except ValueError:
            print(f"Warning: Invalid CAMERA_INDEX value '{os.environ['CAMERA_INDEX']}', using default")
    
    if 'CAMERA_WIDTH' in os.environ:
        try:
            config.camera_width = int(os.environ['CAMERA_WIDTH'])
        except ValueError:
            print(f"Warning: Invalid CAMERA_WIDTH value '{os.environ['CAMERA_WIDTH']}', using default")
    
    if 'CAMERA_HEIGHT' in os.environ:
        try:
            config.camera_height = int(os.environ['CAMERA_HEIGHT'])
        except ValueError:
            print(f"Warning: Invalid CAMERA_HEIGHT value '{os.environ['CAMERA_HEIGHT']}', using default")
    
    return config
