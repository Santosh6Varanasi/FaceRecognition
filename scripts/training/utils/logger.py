"""
Logging utilities with configurable verbosity
"""

import logging
import sys
from typing import Optional


class ScriptLogger:
    """
    Configurable logger for the training script with support for verbose mode.
    """
    
    def __init__(self, name: str = "api_training_script", verbose: bool = False):
        """
        Initialize logger with specified verbosity level.
        
        Args:
            name: Logger name
            verbose: If True, set level to DEBUG; otherwise INFO
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Console handler with formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Format: [LEVEL] message (verbose) or just message (normal)
        if verbose:
            formatter = logging.Formatter(
                '[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter('%(message)s')
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message (only in verbose mode)"""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(f"⚠ WARNING: {message}")
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(f"✗ ERROR: {message}")
    
    def success(self, message: str):
        """Log success message"""
        self.logger.info(f"✓ {message}")
    
    def header(self, text: str):
        """Print formatted header"""
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"  {text}")
        self.logger.info(separator)
    
    def step(self, step_num: int, text: str):
        """Print formatted step"""
        self.logger.info(f"\n[Step {step_num}] {text}")


# Global logger instance (will be initialized in main)
_logger: Optional[ScriptLogger] = None


def get_logger() -> ScriptLogger:
    """Get the global logger instance"""
    global _logger
    if _logger is None:
        _logger = ScriptLogger()
    return _logger


def init_logger(verbose: bool = False) -> ScriptLogger:
    """
    Initialize the global logger with specified verbosity.
    
    Args:
        verbose: Enable verbose logging
        
    Returns:
        Configured logger instance
    """
    global _logger
    _logger = ScriptLogger(verbose=verbose)
    return _logger
