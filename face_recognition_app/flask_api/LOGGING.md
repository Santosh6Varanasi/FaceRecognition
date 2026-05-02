# Flask Logging System

This document describes the centralized logging system implemented for the Flask API.

## Overview

The Flask API uses a comprehensive logging system with:
- **JSON formatted structured logging** for machine readability
- **Rotating file handlers** (100MB max, 5 backups)
- **Separate log files** for app logs, errors, and performance metrics
- **Correlation ID tracking** for distributed tracing
- **Sensitive data sanitization** to prevent exposure of passwords and tokens
- **Performance monitoring** with warnings for slow operations

## Log Files

All logs are stored in the `logs/flask/` directory:

- **app.log** - All application logs (DEBUG and above)
- **error.log** - Error logs only (ERROR and above)
- **performance.log** - Performance metrics and warnings

## Configuration

### Environment Variables

Configure logging via environment variables in `.env`:

```bash
# Log directory path (default: ../../logs/flask)
LOG_DIR=/path/to/logs/flask

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Development default: DEBUG, Production default: INFO
LOG_LEVEL=DEBUG
```

### Log Levels

- **DEBUG** - Detailed information for debugging (development)
- **INFO** - General informational messages (production)
- **WARNING** - Warning messages for potential issues
- **ERROR** - Error messages for failures
- **CRITICAL** - Critical errors requiring immediate attention

## Features

### 1. Request/Response Logging

All API endpoints are decorated with `@log_request_response` which logs:

- Request method, path, headers, query parameters
- Request body (sanitized for POST/PUT/PATCH)
- Response status code and processing time
- Correlation ID for distributed tracing

Example log entry:
```json
{
  "timestamp": "2026-04-30T18:30:45.123456Z",
  "level": "INFO",
  "service": "flask-api",
  "message": "[angular-1714502445123-abc123] Request: GET /api/videos",
  "correlation_id": "angular-1714502445123-abc123",
  "method": "GET",
  "path": "/api/videos",
  "query_params": {"page": "1", "page_size": "20"}
}
```

### 2. Correlation ID Tracking

Correlation IDs are extracted from the `X-Correlation-ID` header and included in all log entries. This enables tracing requests across multiple services (Angular → Next.js → Flask).

Format: `{service}-{timestamp}-{random}`

Example: `angular-1714502445123-abc123`

### 3. Sensitive Data Sanitization

The logging system automatically sanitizes sensitive data from logs:

- Passwords
- Tokens (access_token, refresh_token, api_token)
- API keys
- Secrets
- Authorization headers

Sanitized values are replaced with `***REDACTED***`.

### 4. Performance Monitoring

The system logs performance metrics for:

- **Request processing time** - Logged for every request
- **Database queries** - Use `log_database_query()` helper
- **Video processing operations** - Use `log_video_processing()` helper
- **Model inference** - Use `log_model_inference()` helper

Performance warnings are logged when operations exceed thresholds:
- Requests > 1000ms
- Database queries > 100ms
- Model inference > 500ms

Example performance log:
```json
{
  "timestamp": "2026-04-30T18:30:45.456789Z",
  "level": "WARNING",
  "service": "flask-api",
  "message": "[angular-1714502445123-abc123] Slow request: POST /api/videos/upload took 1234.56ms",
  "correlation_id": "angular-1714502445123-abc123",
  "method": "POST",
  "path": "/api/videos/upload",
  "duration_ms": 1234.56,
  "threshold_ms": 1000
}
```

### 5. Error Logging

All errors are logged with full stack traces and correlation IDs:

```json
{
  "timestamp": "2026-04-30T18:30:45.789012Z",
  "level": "ERROR",
  "service": "flask-api",
  "message": "[angular-1714502445123-abc123] Error: ValueError: Invalid video format",
  "correlation_id": "angular-1714502445123-abc123",
  "error_type": "ValueError",
  "error_message": "Invalid video format",
  "stack_trace": "Traceback (most recent call last):\n  File ..."
}
```

## Usage

### Applying Logging to Routes

Decorate route handlers with `@log_request_response`:

```python
from middleware.logging_middleware import log_request_response

@video_bp.route("/upload", methods=["POST"])
@log_request_response
def upload_video():
    # Your route logic here
    return jsonify({"status": "success"}), 200
```

### Logging Performance Metrics

Use the helper functions for performance logging:

```python
from middleware.logging_middleware import (
    log_database_query,
    log_video_processing,
    log_model_inference
)

# Log database query
start_time = time.time()
result = db.execute(query)
duration_ms = (time.time() - start_time) * 1000
log_database_query(query, duration_ms)

# Log video processing
start_time = time.time()
process_video_frames(video_id)
duration_ms = (time.time() - start_time) * 1000
log_video_processing("frame_extraction", duration_ms, video_id)

# Log model inference
start_time = time.time()
detections = model.predict(frame)
duration_ms = (time.time() - start_time) * 1000
log_model_inference(duration_ms, num_faces=len(detections))
```

### Manual Logging

Use the Flask app logger for manual logging:

```python
from flask import current_app, g

# Get correlation ID from request context
correlation_id = getattr(g, 'correlation_id', 'unknown')

# Log with correlation ID
current_app.logger.info(
    f"[{correlation_id}] Custom log message",
    extra={'extra': {
        'correlation_id': correlation_id,
        'custom_field': 'value'
    }}
)
```

## Log Rotation

Logs are automatically rotated when they reach 100MB:
- Maximum file size: 100MB
- Backup count: 5 files
- Rotated files are compressed (.gz)

Old log files are named:
- `app.log.1`, `app.log.2`, etc.
- Compressed: `app.log.1.gz`, `app.log.2.gz`, etc.

## Log Retention

Logs should be retained for at least 30 days as per requirements. Implement automated cleanup using a cron job or scheduled task:

```bash
# Delete logs older than 30 days
find logs/flask -name "*.log.*" -mtime +30 -delete
```

## Security Considerations

1. **File Permissions** - Ensure log files have appropriate permissions (600 - owner read/write only)
2. **Sensitive Data** - All sensitive data is automatically sanitized
3. **Log Access** - Restrict access to log files to authorized personnel only
4. **Log Retention** - Implement automated cleanup to comply with data retention policies

## Troubleshooting

### Logs Not Being Created

1. Check that the log directory exists and is writable
2. Verify `LOG_DIR` environment variable is set correctly
3. Check Flask app initialization logs for errors

### Missing Correlation IDs

1. Ensure Angular frontend includes `X-Correlation-ID` header in requests
2. Verify Next.js middleware forwards correlation IDs to Flask
3. Check that `@log_request_response` decorator is applied to routes

### Performance Warnings

If you see many performance warnings:
1. Review slow operations and optimize
2. Consider caching frequently accessed data
3. Optimize database queries
4. Profile video processing and model inference

## Requirements Mapping

This logging system satisfies the following requirements:

- **7.1** - Request method, path, headers, and body logging
- **7.2** - Response status code, headers, and body logging
- **7.3** - Request processing time logging
- **7.4** - Correlation ID tracking
- **7.5** - Error logging with full stack traces
- **7.6** - Sensitive data sanitization
- **7.7** - Structured JSON logging
- **9.4** - Log rotation (100MB, 5 backups)
- **9.8** - Automatic log directory creation
- **10.5** - Correlation ID extraction from headers
- **13.1-13.4** - Configurable log levels per environment
- **14.1** - Request processing time logging
- **14.3** - Performance warnings for slow requests (>1000ms)
- **14.5** - Database query execution time logging
- **14.6** - Video processing operation duration logging
- **14.7** - Model inference time logging
