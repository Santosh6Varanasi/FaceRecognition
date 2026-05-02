"""
Flask Error Handler Middleware

This module provides centralized error handling for Flask with:
- Comprehensive error logging with full stack traces
- Correlation ID tracking in error logs
- User-friendly error responses
- HTTP status code mapping

Requirements: 7.5
"""

from flask import jsonify, request, g
import logging
import traceback
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class ApiException(Exception):
    """
    Custom exception for API errors with status code and error code.
    
    Attributes:
        message: Error message
        status_code: HTTP status code
        code: Error code identifier
    """
    
    def __init__(self, message: str, status_code: int = 400, code: str = 'API_ERROR'):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def register_error_handlers(app) -> None:
    """
    Register error handlers for the Flask application.
    
    Handles:
    - ApiException: Custom API exceptions
    - 404 Not Found errors
    - 500 Internal Server errors
    - Generic exceptions
    
    All errors are logged with correlation ID and full stack traces.
    
    Args:
        app: Flask application instance
        
    Requirements: 7.5
    """
    
    @app.errorhandler(ApiException)
    def handle_api_exception(error: ApiException) -> Tuple[Dict[str, Any], int]:
        """Handle custom API exceptions"""
        correlation_id = getattr(g, 'correlation_id', request.headers.get('X-Correlation-ID', 'unknown'))
        
        logger.error(
            f"[{correlation_id}] API Error: {error.message}",
            extra={'extra': {
                'correlation_id': correlation_id,
                'status_code': error.status_code,
                'error_code': error.code,
                'error_message': error.message,
                'path': request.path,
                'method': request.method
            }}
        )
        
        return jsonify({
            'success': False,
            'error': {
                'code': error.code,
                'message': error.message
            }
        }), error.status_code
    
    @app.errorhandler(404)
    def handle_not_found(error) -> Tuple[Dict[str, Any], int]:
        """Handle 404 Not Found errors"""
        correlation_id = getattr(g, 'correlation_id', request.headers.get('X-Correlation-ID', 'unknown'))
        
        logger.warning(
            f"[{correlation_id}] Not Found: {request.method} {request.path}",
            extra={'extra': {
                'correlation_id': correlation_id,
                'status_code': 404,
                'path': request.path,
                'method': request.method
            }}
        )
        
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Resource not found: {request.path}'
            }
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error) -> Tuple[Dict[str, Any], int]:
        """Handle 500 Internal Server errors"""
        correlation_id = getattr(g, 'correlation_id', request.headers.get('X-Correlation-ID', 'unknown'))
        
        logger.error(
            f"[{correlation_id}] Internal Server Error: {str(error)}",
            extra={'extra': {
                'correlation_id': correlation_id,
                'status_code': 500,
                'error_message': str(error),
                'stack_trace': traceback.format_exc(),
                'path': request.path,
                'method': request.method
            }},
            exc_info=True
        )
        
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred'
            }
        }), 500
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception) -> Tuple[Dict[str, Any], int]:
        """Handle all unhandled exceptions"""
        correlation_id = getattr(g, 'correlation_id', request.headers.get('X-Correlation-ID', 'unknown'))
        
        logger.error(
            f"[{correlation_id}] Unhandled Exception: {type(error).__name__}: {str(error)}",
            extra={'extra': {
                'correlation_id': correlation_id,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'stack_trace': traceback.format_exc(),
                'path': request.path,
                'method': request.method
            }},
            exc_info=True
        )
        
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred'
            }
        }), 500
    
    app.logger.info("Error handlers registered")
