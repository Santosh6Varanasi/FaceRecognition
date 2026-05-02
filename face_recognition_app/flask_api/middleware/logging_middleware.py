"""
Flask Logging Middleware

This module provides middleware for comprehensive request/response logging with:
- Request method, path, headers, query parameters, and body logging
- Response status code and processing time logging
- Correlation ID extraction and propagation
- Sensitive data sanitization
- Performance monitoring and warnings
- Error logging with full stack traces

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 10.5, 14.1, 14.3, 14.5, 14.6, 14.7
"""

from flask import request, g, jsonify
from functools import wraps
import time
import logging
import traceback
from typing import Any, Dict, Callable, Optional

# Get loggers
logger = logging.getLogger(__name__)
perf_logger = logging.getLogger('performance')


def sanitize_sensitive_data(data: Any) -> Any:
    """
    Remove sensitive data from logs to prevent exposure of passwords, tokens, etc.
    
    Sanitizes the following keys (case-insensitive):
    - password
    - token
    - api_key
    - secret
    - authorization
    - access_token
    - refresh_token
    
    Args:
        data: Data to sanitize (dict, list, or other)
        
    Returns:
        Sanitized copy of the data
        
    Requirements: 7.6
    """
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = [
        'password', 'token', 'api_key', 'secret', 'authorization',
        'access_token', 'refresh_token', 'api_secret', 'private_key'
    ]
    
    sanitized = {}
    for key, value in data.items():
        # Check if key contains any sensitive keyword (case-insensitive)
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_sensitive_data(value)
        elif isinstance(value, list):
            # Sanitize lists of dictionaries
            sanitized[key] = [
                sanitize_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


def log_request_response(f: Callable) -> Callable:
    """
    Decorator to log request and response details for Flask routes.
    
    Logs:
    - Request: method, path, headers, query parameters, body (sanitized)
    - Response: status code, processing time
    - Performance warnings for slow requests (>1000ms)
    - Correlation ID for distributed tracing
    
    Usage:
        @app.route('/api/endpoint')
        @log_request_response
        def my_endpoint():
            return {'data': 'value'}
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 10.5, 14.1, 14.3
    """
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ====================================================================
        # Extract or generate correlation ID
        # ====================================================================
        correlation_id = request.headers.get('X-Correlation-ID', 'unknown')
        g.correlation_id = correlation_id
        
        # ====================================================================
        # Log incoming request
        # ====================================================================
        request_data = {
            'correlation_id': correlation_id,
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.args),
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'unknown')
        }
        
        # Sanitize and log headers (exclude sensitive headers)
        sanitized_headers = sanitize_sensitive_data(dict(request.headers))
        request_data['headers'] = sanitized_headers
        
        logger.info(
            f"[{correlation_id}] Request: {request.method} {request.path}",
            extra={'extra': request_data}
        )
        
        # Log request body for POST/PUT/PATCH (sanitized)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.is_json:
                    body = request.get_json()
                    sanitized_body = sanitize_sensitive_data(body)
                    logger.debug(
                        f"[{correlation_id}] Request body",
                        extra={'extra': {'correlation_id': correlation_id, 'body': sanitized_body}}
                    )
            except Exception as e:
                logger.warning(
                    f"[{correlation_id}] Could not parse request body: {str(e)}",
                    extra={'extra': {'correlation_id': correlation_id}}
                )
        
        # ====================================================================
        # Execute the route handler
        # ====================================================================
        start_time = time.time()
        
        try:
            response = f(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract status code from response
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            elif hasattr(response, 'status_code'):
                status_code = response.status_code
            else:
                status_code = 200
            
            # ================================================================
            # Log successful response
            # ================================================================
            response_data = {
                'correlation_id': correlation_id,
                'status_code': status_code,
                'duration_ms': round(duration_ms, 2)
            }
            
            logger.info(
                f"[{correlation_id}] Response: {status_code} ({duration_ms:.2f}ms)",
                extra={'extra': response_data}
            )
            
            # ================================================================
            # Log performance warning if request is slow (>1000ms)
            # Requirements: 14.3
            # ================================================================
            if duration_ms > 1000:
                perf_logger.warning(
                    f"[{correlation_id}] Slow request: {request.method} {request.path} took {duration_ms:.2f}ms",
                    extra={'extra': {
                        'correlation_id': correlation_id,
                        'method': request.method,
                        'path': request.path,
                        'duration_ms': round(duration_ms, 2),
                        'threshold_ms': 1000
                    }}
                )
            
            return response
            
        except Exception as e:
            # ================================================================
            # Log error with full stack trace
            # Requirements: 7.5
            # ================================================================
            duration_ms = (time.time() - start_time) * 1000
            
            error_data = {
                'correlation_id': correlation_id,
                'method': request.method,
                'path': request.path,
                'duration_ms': round(duration_ms, 2),
                'error_type': type(e).__name__,
                'error_message': str(e),
                'stack_trace': traceback.format_exc()
            }
            
            logger.error(
                f"[{correlation_id}] Error: {type(e).__name__}: {str(e)}",
                extra={'extra': error_data},
                exc_info=True
            )
            
            # Re-raise the exception to be handled by Flask error handlers
            raise
    
    return decorated_function


def log_database_query(query: str, duration_ms: float, correlation_id: Optional[str] = None) -> None:
    """
    Log database query execution time.
    
    Args:
        query: SQL query string (first 100 chars)
        duration_ms: Query execution time in milliseconds
        correlation_id: Request correlation ID
        
    Requirements: 14.5
    """
    if correlation_id is None:
        correlation_id = getattr(g, 'correlation_id', 'unknown')
    
    query_preview = query[:100] + '...' if len(query) > 100 else query
    
    perf_logger.info(
        f"[{correlation_id}] Database query: {duration_ms:.2f}ms",
        extra={'extra': {
            'correlation_id': correlation_id,
            'query_preview': query_preview,
            'duration_ms': round(duration_ms, 2),
            'operation_type': 'database_query'
        }}
    )
    
    # Warn if query is slow (>100ms)
    if duration_ms > 100:
        perf_logger.warning(
            f"[{correlation_id}] Slow database query: {duration_ms:.2f}ms",
            extra={'extra': {
                'correlation_id': correlation_id,
                'query_preview': query_preview,
                'duration_ms': round(duration_ms, 2),
                'threshold_ms': 100
            }}
        )


def log_video_processing(operation: str, duration_ms: float, video_id: Optional[int] = None, 
                        correlation_id: Optional[str] = None) -> None:
    """
    Log video processing operation duration.
    
    Args:
        operation: Operation name (e.g., 'frame_extraction', 'face_detection')
        duration_ms: Operation duration in milliseconds
        video_id: Video ID being processed
        correlation_id: Request correlation ID
        
    Requirements: 14.6
    """
    if correlation_id is None:
        correlation_id = getattr(g, 'correlation_id', 'unknown')
    
    perf_logger.info(
        f"[{correlation_id}] Video processing - {operation}: {duration_ms:.2f}ms",
        extra={'extra': {
            'correlation_id': correlation_id,
            'operation': operation,
            'video_id': video_id,
            'duration_ms': round(duration_ms, 2),
            'operation_type': 'video_processing'
        }}
    )
    
    # Warn if operation is slow (>1000ms)
    if duration_ms > 1000:
        perf_logger.warning(
            f"[{correlation_id}] Slow video processing - {operation}: {duration_ms:.2f}ms",
            extra={'extra': {
                'correlation_id': correlation_id,
                'operation': operation,
                'video_id': video_id,
                'duration_ms': round(duration_ms, 2),
                'threshold_ms': 1000
            }}
        )


def log_model_inference(duration_ms: float, num_faces: int = 0, 
                       correlation_id: Optional[str] = None) -> None:
    """
    Log model inference time.
    
    Args:
        duration_ms: Inference duration in milliseconds
        num_faces: Number of faces detected
        correlation_id: Request correlation ID
        
    Requirements: 14.7
    """
    if correlation_id is None:
        correlation_id = getattr(g, 'correlation_id', 'unknown')
    
    perf_logger.info(
        f"[{correlation_id}] Model inference: {duration_ms:.2f}ms ({num_faces} faces)",
        extra={'extra': {
            'correlation_id': correlation_id,
            'duration_ms': round(duration_ms, 2),
            'num_faces': num_faces,
            'operation_type': 'model_inference'
        }}
    )
    
    # Warn if inference is slow (>500ms)
    if duration_ms > 500:
        perf_logger.warning(
            f"[{correlation_id}] Slow model inference: {duration_ms:.2f}ms",
            extra={'extra': {
                'correlation_id': correlation_id,
                'duration_ms': round(duration_ms, 2),
                'num_faces': num_faces,
                'threshold_ms': 500
            }}
        )
