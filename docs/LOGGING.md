# Logging Infrastructure Documentation

## Overview

This document describes the centralized logging infrastructure for the face recognition application. The logging system provides structured, JSON-formatted logs with correlation IDs for tracing requests across multiple services (Angular, Next.js, Flask).

## Directory Structure

```
logs/
├── .gitkeep                    # Ensures logs directory is tracked by git
├── nextjs/                     # Next.js backend logs
│   ├── .gitkeep
│   ├── app-YYYY-MM-DD.log      # Application logs
│   ├── error-YYYY-MM-DD.log    # Error logs
│   └── access-YYYY-MM-DD.log   # Access logs
└── flask/                      # Flask API logs
    ├── .gitkeep
    ├── app-YYYY-MM-DD.log      # Application logs
    ├── error-YYYY-MM-DD.log    # Error logs
    └── performance-YYYY-MM-DD.log  # Performance metrics
```

## Environment Variables

### LOG_DIR
- **Description**: Path to the centralized logs directory
- **Default**: `../logs` (relative to service directory)
- **Example**: `/var/log/face-recognition` (absolute path)
- **Used by**: Flask API, Next.js Backend

### LOG_LEVEL
- **Description**: Minimum log level to record
- **Valid values**: 
  - Flask: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Next.js: `debug`, `info`, `warn`, `error`
- **Default**: 
  - Development: `DEBUG` / `debug`
  - Production: `INFO` / `info`
- **Used by**: Flask API, Next.js Backend

## Configuration

### Flask API

The Flask API uses Python's built-in `logging` module with rotating file handlers.

**Configuration file**: `flask_api/logging_config.py`

**Features**:
- JSON-formatted logs for machine readability
- Rotating file handlers (100MB max size, 5 backup files)
- Separate log files for app, error, and performance logs
- Automatic log directory creation
- Sensitive data sanitization (passwords, tokens, API keys)
- Correlation ID support for request tracing

**Log format**:
```json
{
  "timestamp": "2026-04-30T18:30:45.123456",
  "level": "INFO",
  "service": "flask-api",
  "message": "Request processed successfully",
  "correlation_id": "flask-1714502445123-abc123",
  "method": "GET",
  "path": "/api/videos",
  "status_code": 200,
  "duration_ms": 45.67
}
```

### Next.js Backend

The Next.js backend uses Winston for structured logging.

**Configuration file**: `nextjs_backend/lib/logger.ts`

**Features**:
- JSON-formatted logs for machine readability
- Rotating file handlers (100MB max size, 5 backup files)
- Separate log files for app and error logs
- Console output in development mode
- Automatic log directory creation
- Correlation ID support for request tracing

**Log format**:
```json
{
  "timestamp": "2026-04-30T18:30:45.123Z",
  "level": "info",
  "service": "nextjs-backend",
  "message": "API request processed",
  "correlationId": "nextjs-1714502445123-xyz789",
  "method": "GET",
  "path": "/api/videos",
  "status": 200,
  "duration": 45.67
}
```

## Log Rotation

Logs are automatically rotated when they reach 100MB in size. The rotation policy:

- **Max file size**: 100MB
- **Max backup files**: 5
- **Compression**: Rotated files are compressed with gzip (`.gz` extension)
- **Retention**: Logs are retained for at least 30 days (manual cleanup required)

### Manual Log Cleanup

To clean up old logs:

```bash
# Remove logs older than 30 days
find logs/ -name "*.log*" -mtime +30 -delete
```

To automate cleanup, add a cron job:

```bash
# Edit crontab
crontab -e

# Add daily cleanup at 2 AM
0 2 * * * find /path/to/logs -name "*.log*" -mtime +30 -delete
```

## Correlation IDs

Correlation IDs enable tracing requests across multiple services. The format is:

```
{service}-{timestamp}-{random}
```

**Example**: `angular-1714502445123-abc123`

### Flow

1. **Angular Frontend** generates a correlation ID when making a request
2. **Next.js Backend** receives the correlation ID in the `X-Correlation-ID` header
3. **Next.js Backend** includes the correlation ID in all log entries
4. **Next.js Backend** forwards the correlation ID to Flask API
5. **Flask API** includes the correlation ID in all log entries

### Searching Logs by Correlation ID

```bash
# Search all logs for a specific correlation ID
grep "angular-1714502445123-abc123" logs/**/*.log

# Search with jq for JSON logs
cat logs/nextjs/app.log | jq 'select(.correlationId == "angular-1714502445123-abc123")'
cat logs/flask/app.log | jq 'select(.correlation_id == "angular-1714502445123-abc123")'
```

## Sensitive Data Sanitization

The logging system automatically sanitizes sensitive data before writing to logs:

**Sanitized fields**:
- `password`
- `token`
- `api_key`
- `secret`
- `authorization`

**Example**:
```json
// Original request body
{
  "username": "john.doe",
  "password": "secret123"
}

// Logged request body
{
  "username": "john.doe",
  "password": "***REDACTED***"
}
```

## Performance Logging

The Flask API includes dedicated performance logging for monitoring slow operations.

**Performance log file**: `logs/flask/performance-YYYY-MM-DD.log`

**Logged metrics**:
- Request processing time
- Database query execution time
- Video processing duration
- Model inference time

**Performance warnings**:
- Requests exceeding 1000ms trigger a warning log entry

**Example**:
```json
{
  "timestamp": "2026-04-30T18:30:45.123456",
  "level": "WARNING",
  "service": "flask-api",
  "message": "Slow request: GET /api/videos took 1234.56ms",
  "correlation_id": "flask-1714502445123-abc123",
  "method": "GET",
  "path": "/api/videos",
  "duration_ms": 1234.56
}
```

## Log Levels

### DEBUG
- Detailed diagnostic information
- Use for development and troubleshooting
- **Not recommended for production** (high volume)

### INFO
- General informational messages
- Request/response logging
- Application lifecycle events
- **Recommended for production**

### WARNING
- Potentially harmful situations
- Performance warnings (slow requests)
- Deprecated feature usage

### ERROR
- Error events that might still allow the application to continue
- Failed requests
- Caught exceptions

### CRITICAL (Flask only)
- Severe error events that might cause the application to abort
- System failures
- Unrecoverable errors

## Viewing Logs

### Real-time Monitoring

```bash
# Tail all Next.js logs
tail -f logs/nextjs/app.log

# Tail all Flask logs
tail -f logs/flask/app.log

# Tail error logs from both services
tail -f logs/nextjs/error.log logs/flask/error.log
```

### Parsing JSON Logs

```bash
# Pretty-print JSON logs
cat logs/nextjs/app.log | jq '.'

# Filter by log level
cat logs/flask/app.log | jq 'select(.level == "ERROR")'

# Filter by time range
cat logs/nextjs/app.log | jq 'select(.timestamp >= "2026-04-30T18:00:00")'

# Extract specific fields
cat logs/flask/app.log | jq '{timestamp, level, message, correlation_id}'
```

### Log Analysis

```bash
# Count errors by type
cat logs/flask/error.log | jq -r '.message' | sort | uniq -c | sort -rn

# Calculate average request duration
cat logs/nextjs/app.log | jq -r 'select(.duration != null) | .duration' | awk '{sum+=$1; count++} END {print sum/count}'

# Find slowest requests
cat logs/flask/performance.log | jq 'select(.duration_ms > 1000)' | jq -s 'sort_by(.duration_ms) | reverse | .[0:10]'
```

## Troubleshooting

### Logs Not Being Created

1. **Check directory permissions**:
   ```bash
   ls -la logs/
   # Ensure the application user has write permissions
   ```

2. **Check LOG_DIR environment variable**:
   ```bash
   echo $LOG_DIR
   # Should point to the logs directory
   ```

3. **Check application logs** (console output in development):
   - Look for "Failed to create log directory" errors
   - Look for "Permission denied" errors

### Log Files Growing Too Large

1. **Verify rotation is working**:
   ```bash
   ls -lh logs/nextjs/
   # Should see .log.1, .log.2, etc. files
   ```

2. **Check rotation configuration**:
   - Max file size: 100MB
   - Max backup files: 5

3. **Manually rotate logs** if needed:
   ```bash
   # Stop the application
   # Rename current log file
   mv logs/nextjs/app.log logs/nextjs/app.log.1
   # Restart the application
   ```

### Missing Correlation IDs

1. **Check Angular interceptor** is registered in `app.config.ts`
2. **Check Next.js middleware** is configured in `middleware.ts`
3. **Check Flask middleware** is applied to routes

### Sensitive Data in Logs

1. **Review sanitization rules** in logging middleware
2. **Add new sensitive field names** to the sanitization list
3. **Report security issue** if sensitive data is found in logs

## Best Practices

1. **Use appropriate log levels**:
   - DEBUG: Detailed diagnostic information
   - INFO: General informational messages
   - WARNING: Potentially harmful situations
   - ERROR: Error events

2. **Include context in log messages**:
   - Always include correlation ID
   - Include relevant request/response details
   - Include error stack traces

3. **Avoid logging sensitive data**:
   - Never log passwords, tokens, or API keys
   - Use sanitization for user-provided data
   - Review logs regularly for sensitive data

4. **Monitor log volume**:
   - Use INFO level in production
   - Use DEBUG level only for troubleshooting
   - Implement log sampling for high-traffic endpoints

5. **Regular log analysis**:
   - Monitor error rates
   - Track performance metrics
   - Identify slow requests
   - Detect anomalies

## Security Considerations

1. **File Permissions**:
   - Log files should be readable only by the application user and administrators
   - Recommended permissions: `600` (owner read/write only)
   - Log directories: `700` (owner read/write/execute only)
   - Use `scripts/set_log_permissions.sh` to set appropriate permissions

2. **Log Retention**:
   - Automated log cleanup after 30 days (configurable)
   - Log rotation at 100MB with 5 backup files
   - Rotated logs are automatically compressed (gzip)
   - See [Log Retention Policy](LOG_RETENTION_POLICY.md) for details
   - Use `scripts/cleanup_logs.py` for automated cleanup

3. **Sensitive Data**:
   - Never log passwords, tokens, or API keys
   - Sanitize user-provided data before logging
   - Review logs regularly for sensitive data leaks
   - Passwords, tokens, and authorization headers are automatically sanitized

4. **Access Control**:
   - Restrict access to log files
   - Use secure methods for log transfer (SSH, SFTP)
   - Implement audit logging for log access
   - Consider encrypting logs at rest for sensitive data

## Future Enhancements

1. **Centralized Log Aggregation**:
   - Integrate with ELK Stack (Elasticsearch, Logstash, Kibana)
   - Integrate with Splunk or Datadog
   - Real-time log streaming and analysis

2. **Alerting**:
   - Configure alerts for error rate thresholds
   - Configure alerts for performance degradation
   - Integrate with PagerDuty or similar services

3. **Log Metrics**:
   - Export log metrics to Prometheus
   - Create Grafana dashboards for visualization
   - Track key performance indicators (KPIs)

4. **Structured Logging Enhancements**:
   - Add request/response body logging (with size limits)
   - Add user context (user ID, session ID)
   - Add deployment version/commit hash

## References

- [Log Retention Policy](LOG_RETENTION_POLICY.md) - Detailed retention and cleanup policy
- [Winston Documentation](https://github.com/winstonjs/winston)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Logging Best Practices](https://www.loggly.com/ultimate-guide/python-logging-basics/)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
