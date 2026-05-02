"""
Flask Logging Configuration Module

This module provides centralized logging configuration for the Flask API with:
- JSON formatted structured logging
- Rotating file handlers for app, error, and performance logs
- Automatic log directory creation
- Environment-based log level configuration
- Console logging for development environments

Requirements: 7.1, 7.2, 7.5, 7.7, 9.4, 9.8, 13.1, 13.2, 13.3, 13.4
"""

import logging
import os
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from typing import Optional, Dict, Any
import gzip
import shutil


# Get log directory from environment or use default
LOG_DIR = os.getenv('LOG_DIR', os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'flask'))


class JSONFormatter(logging.Formatter):
    """
    Custom formatter to output logs in JSON format for machine readability.
    
    Outputs structured log entries with:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - service: Service identifier (flask-api)
    - message: Log message
    - module, function, line: Source code location
    - correlation_id: Request correlation ID (if present)
    - extra: Additional context fields
    - exception: Exception traceback (if present)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON formatted log entry as a string
        """
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'service': 'flask-api',
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        # Add extra fields from the record
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            log_data['stack_trace'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class CompressedRotatingFileHandler(RotatingFileHandler):
    """
    Custom rotating file handler that compresses rotated log files using gzip.
    
    When a log file is rotated, the old file is compressed to save disk space.
    Rotated files are named: filename.log.1.gz, filename.log.2.gz, etc.
    
    Requirements: 9.6
    """
    
    def doRollover(self):
        """
        Do a rollover and compress the rotated file.
        
        This method is called when the current log file reaches maxBytes.
        It closes the current file, renames it, compresses it, and opens a new file.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Rotate existing backup files
        for i in range(self.backupCount - 1, 0, -1):
            sfn = f"{self.baseFilename}.{i}.gz"
            dfn = f"{self.baseFilename}.{i + 1}.gz"
            if os.path.exists(sfn):
                if os.path.exists(dfn):
                    os.remove(dfn)
                os.rename(sfn, dfn)
        
        # Compress the current log file
        dfn = f"{self.baseFilename}.1.gz"
        if os.path.exists(dfn):
            os.remove(dfn)
        
        # Compress the log file
        if os.path.exists(self.baseFilename):
            with open(self.baseFilename, 'rb') as f_in:
                with gzip.open(dfn, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(self.baseFilename)
        
        # Open new log file
        self.mode = 'w'
        self.stream = self._open()


def setup_logging(app) -> logging.Logger:
    """
    Configure logging for Flask application.
    
    Sets up:
    - JSON formatted logging
    - Rotating file handlers (100MB max, 5 backups)
    - Separate files for app logs, errors, and performance metrics
    - Console logging for development environments
    - Environment-based log level configuration
    
    Args:
        app: Flask application instance
        
    Returns:
        Configured logger instance
        
    Requirements: 7.1, 7.2, 7.5, 7.7, 9.4, 9.8, 13.1, 13.2, 13.3, 13.4
    """
    
    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Determine log level based on environment
    # Production: INFO, Development: DEBUG
    env = app.config.get('ENV', 'production')
    log_level_str = os.getenv('LOG_LEVEL', 'INFO' if env == 'production' else 'DEBUG')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Set log level for app logger
    app.logger.setLevel(log_level)
    
    # Remove default handlers to avoid duplicate logs
    app.logger.handlers.clear()
    
    # Create JSON formatter
    json_formatter = JSONFormatter()
    
    # ========================================================================
    # App Log Handler - All logs (DEBUG and above)
    # ========================================================================
    app_handler = CompressedRotatingFileHandler(
        os.path.join(LOG_DIR, 'app.log'),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(json_formatter)
    app.logger.addHandler(app_handler)
    
    # ========================================================================
    # Error Log Handler - Errors only (ERROR and above)
    # ========================================================================
    error_handler = CompressedRotatingFileHandler(
        os.path.join(LOG_DIR, 'error.log'),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    app.logger.addHandler(error_handler)
    
    # ========================================================================
    # Performance Log Handler - Performance metrics
    # ========================================================================
    perf_handler = CompressedRotatingFileHandler(
        os.path.join(LOG_DIR, 'performance.log'),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(json_formatter)
    
    # Create separate performance logger
    perf_logger = logging.getLogger('performance')
    perf_logger.setLevel(logging.INFO)
    perf_logger.addHandler(perf_handler)
    perf_logger.propagate = False  # Don't propagate to root logger
    
    # ========================================================================
    # Console Handler - Development only
    # ========================================================================
    if env != 'production':
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] %(message)s',
            defaults={'correlation_id': 'N/A'}
        ))
        app.logger.addHandler(console_handler)
    
    app.logger.info(
        f"Logging configured: level={log_level_str}, dir={LOG_DIR}",
        extra={'log_level': log_level_str, 'log_dir': LOG_DIR}
    )
    
    return app.logger
