# Log Retention and Cleanup Policy

## Overview

This document describes the log retention policy and cleanup procedures for the face recognition application. The policy ensures that logs are retained for an appropriate period for debugging and compliance purposes while preventing excessive disk usage.

**Requirements**: 9.4, 9.5, 9.6, 9.9

## Policy Summary

| Aspect | Configuration |
|--------|---------------|
| **Retention Period** | 30 days |
| **Rotation Trigger** | 100 MB file size |
| **Backup Files** | 5 rotated files per log type |
| **Compression** | Enabled (gzip) |
| **File Permissions** | 600 (owner read/write only) |
| **Directory Permissions** | 700 (owner read/write/execute only) |

## Log Rotation Configuration

### Flask API (Python)

The Flask API uses a custom `CompressedRotatingFileHandler` that extends Python's `RotatingFileHandler`:

```python
# Configuration in flask_api/logging_config.py
CompressedRotatingFileHandler(
    filename='logs/flask/app.log',
    maxBytes=100 * 1024 * 1024,  # 100MB
    backupCount=5                 # Keep 5 backup files
)
```

**Rotation Behavior**:
- When `app.log` reaches 100MB, it is rotated
- Existing backups are renamed: `app.log.1.gz` → `app.log.2.gz`, etc.
- Current log is compressed to `app.log.1.gz`
- New `app.log` file is created
- Oldest backup (`app.log.6.gz`) is deleted if it exists

**Log Files**:
- `app.log` - Current application log
- `app.log.1.gz` - Most recent rotated log (compressed)
- `app.log.2.gz` through `app.log.5.gz` - Older rotated logs
- `error.log` and `performance.log` follow the same pattern

### Next.js Backend (TypeScript)

The Next.js backend uses Winston with `winston-daily-rotate-file`:

```typescript
// Configuration in nextjs_backend/lib/logger.ts
new DailyRotateFile({
    filename: 'logs/nextjs/app-%DATE%.log',
    datePattern: 'YYYY-MM-DD',
    zippedArchive: true,  // Compress rotated files
    maxSize: '100m',      // 100MB
    maxFiles: '5'         // Keep 5 backup files
})
```

**Rotation Behavior**:
- Logs are rotated daily at midnight
- Files are also rotated when they reach 100MB
- Rotated files are automatically compressed with gzip
- Files are named with date: `app-2026-04-30.log`, `app-2026-04-29.log.gz`, etc.
- Only the 5 most recent files are kept

**Log Files**:
- `app-2026-04-30.log` - Current day's application log
- `app-2026-04-29.log.gz` - Previous day's log (compressed)
- `error-2026-04-30.log` - Current day's error log
- `error-2026-04-29.log.gz` - Previous day's error log (compressed)

## Automated Cleanup

### Cleanup Scripts

Three cleanup scripts are provided for different platforms:

#### 1. Python Script (Cross-platform)

**Location**: `scripts/cleanup_logs.py`

**Usage**:
```bash
# Dry run (see what would be deleted)
python scripts/cleanup_logs.py --dry-run

# Delete logs older than 30 days (default)
python scripts/cleanup_logs.py

# Delete logs older than 7 days
python scripts/cleanup_logs.py --days 7

# Specify custom log directory
python scripts/cleanup_logs.py --log-dir /var/logs
```

**Features**:
- Cross-platform (Windows, Linux, macOS)
- Dry-run mode for testing
- Configurable retention period
- Human-readable output with file sizes
- Preserves `.gitkeep` files
- Only deletes log files (`.log`, `.log.*`, `.gz`)

#### 2. Shell Script (Linux/macOS)

**Location**: `scripts/cleanup_logs.sh`

**Usage**:
```bash
# Make executable
chmod +x scripts/cleanup_logs.sh

# Run with defaults (30 days)
./scripts/cleanup_logs.sh

# Specify retention period and log directory
./scripts/cleanup_logs.sh 7 /var/logs
```

#### 3. Batch Script (Windows)

**Location**: `scripts/cleanup_logs.bat`

**Usage**:
```cmd
REM Run with defaults (30 days)
cleanup_logs.bat

REM Specify retention period and log directory
cleanup_logs.bat 7 C:\logs
```

### Scheduling Automated Cleanup

#### Linux/macOS (cron)

Add to crontab (`crontab -e`):

```cron
# Run log cleanup daily at 2:00 AM
0 2 * * * /path/to/scripts/cleanup_logs.sh >> /var/log/log_cleanup.log 2>&1

# Or use Python script
0 2 * * * /usr/bin/python3 /path/to/scripts/cleanup_logs.py >> /var/log/log_cleanup.log 2>&1
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Log Cleanup"
4. Trigger: Daily at 2:00 AM
5. Action: Start a program
   - Program: `C:\path\to\scripts\cleanup_logs.bat`
   - Or: `python.exe`
   - Arguments: `C:\path\to\scripts\cleanup_logs.py`
6. Finish

#### Docker/Kubernetes (CronJob)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: log-cleanup
spec:
  schedule: "0 2 * * *"  # Daily at 2:00 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: log-cleanup
            image: python:3.11-slim
            command:
            - python
            - /scripts/cleanup_logs.py
            volumeMounts:
            - name: logs
              mountPath: /logs
            - name: scripts
              mountPath: /scripts
          volumes:
          - name: logs
            persistentVolumeClaim:
              claimName: logs-pvc
          - name: scripts
            configMap:
              name: cleanup-scripts
          restartPolicy: OnFailure
```

## File Permissions

### Security Policy

Log files contain sensitive information and must be protected from unauthorized access.

**Permissions**:
- **Log files**: `600` (rw-------) - Owner read/write only
- **Log directories**: `700` (rwx------) - Owner read/write/execute only
- **Documentation files**: `644` (rw-r--r--) - Owner read/write, others read

### Setting Permissions

#### Automated Script (Linux/macOS)

**Location**: `scripts/set_log_permissions.sh`

**Usage**:
```bash
# Make executable
chmod +x scripts/set_log_permissions.sh

# Run as owner
./scripts/set_log_permissions.sh

# Run with sudo to change ownership
sudo ./scripts/set_log_permissions.sh /path/to/logs user:group
```

#### Manual Commands

**Linux/macOS**:
```bash
# Set directory permissions
find logs -type d -exec chmod 700 {} \;

# Set log file permissions
find logs -type f \( -name "*.log" -o -name "*.log.*" -o -name "*.gz" \) -exec chmod 600 {} \;

# Set ownership (run as root)
chown -R appuser:appgroup logs/
```

**Windows**:
```powershell
# Remove inheritance and set explicit permissions
icacls logs /inheritance:r

# Grant full control to owner only
icacls logs /grant:r "OWNER:(OI)(CI)F"

# Apply to all subdirectories and files
icacls logs\* /inheritance:r /grant:r "OWNER:(OI)(CI)F"
```

### Verification

Check current permissions:

```bash
# Linux/macOS
ls -la logs/
ls -la logs/flask/
ls -la logs/nextjs/

# Windows
icacls logs
```

Expected output (Linux/macOS):
```
drwx------  5 appuser appgroup  4096 Apr 30 10:00 logs/
drwx------  2 appuser appgroup  4096 Apr 30 10:00 logs/flask/
drwx------  2 appuser appgroup  4096 Apr 30 10:00 logs/nextjs/
-rw-------  1 appuser appgroup  1024 Apr 30 10:00 logs/flask/app.log
-rw-------  1 appuser appgroup  2048 Apr 30 09:00 logs/flask/app.log.1.gz
```

## Compliance Considerations

### Data Retention Requirements

Different jurisdictions and industries have different log retention requirements:

| Jurisdiction/Industry | Typical Requirement |
|----------------------|---------------------|
| **GDPR (EU)** | Minimum necessary, typically 30-90 days |
| **HIPAA (Healthcare)** | 6 years |
| **SOX (Financial)** | 7 years |
| **PCI DSS (Payment)** | 1 year minimum, 3 months online |
| **General Security** | 30-90 days |

**Current Policy**: 30 days (suitable for general security and GDPR compliance)

**Adjusting Retention Period**:
```bash
# For compliance requirements, adjust the retention period
python scripts/cleanup_logs.py --days 90   # 90 days
python scripts/cleanup_logs.py --days 365  # 1 year
python scripts/cleanup_logs.py --days 2555 # 7 years
```

### Personal Data in Logs

Logs may contain personal data subject to privacy regulations:

**Sensitive Data Sanitization**:
- Passwords: ✓ Sanitized
- API tokens: ✓ Sanitized
- Authorization headers: ✓ Sanitized
- User emails: ⚠️ May be present (consider sanitizing)
- IP addresses: ⚠️ Present (may be considered personal data)

**Recommendations**:
1. Review logs regularly for sensitive data
2. Implement additional sanitization if needed
3. Document what personal data is logged
4. Ensure retention period complies with regulations
5. Provide mechanism for data deletion requests

## Monitoring and Alerts

### Disk Space Monitoring

Monitor disk space to prevent log files from filling the disk:

```bash
# Check disk usage
df -h /path/to/logs

# Check log directory size
du -sh logs/
du -sh logs/flask/
du -sh logs/nextjs/
```

### Recommended Alerts

Set up alerts for:
- **Disk usage > 80%**: Warning
- **Disk usage > 90%**: Critical
- **Log cleanup failures**: Error
- **Unusual log growth**: Warning (e.g., >1GB/day)

### Log Rotation Monitoring

Verify log rotation is working:

```bash
# Check for rotated files
ls -lh logs/flask/*.gz
ls -lh logs/nextjs/*.gz

# Check file ages
find logs -name "*.log" -mtime +1  # Files older than 1 day
find logs -name "*.gz" -mtime +30  # Compressed files older than 30 days
```

## Troubleshooting

### Issue: Logs Not Rotating

**Symptoms**: Log file grows beyond 100MB

**Causes**:
- Application not restarting after configuration change
- File permissions preventing rotation
- Disk space full

**Solutions**:
```bash
# Check file size
ls -lh logs/flask/app.log

# Check disk space
df -h

# Check permissions
ls -la logs/flask/

# Restart application
systemctl restart flask-api
systemctl restart nextjs-backend
```

### Issue: Cleanup Script Not Running

**Symptoms**: Old log files not being deleted

**Causes**:
- Cron job not configured
- Script permissions incorrect
- Script path incorrect in cron

**Solutions**:
```bash
# Check cron jobs
crontab -l

# Check script permissions
ls -l scripts/cleanup_logs.sh

# Test script manually
./scripts/cleanup_logs.sh --dry-run

# Check cron logs
grep CRON /var/log/syslog
```

### Issue: Permission Denied Errors

**Symptoms**: Cannot read/write log files

**Causes**:
- Incorrect file permissions
- Application running as wrong user
- SELinux/AppArmor restrictions

**Solutions**:
```bash
# Check current permissions
ls -la logs/

# Fix permissions
sudo ./scripts/set_log_permissions.sh

# Check application user
ps aux | grep flask
ps aux | grep node

# Check SELinux (if applicable)
getenforce
sestatus
```

## Best Practices

1. **Regular Monitoring**: Check log sizes and disk usage weekly
2. **Test Cleanup**: Run cleanup script with `--dry-run` before production
3. **Backup Important Logs**: Archive logs before cleanup if needed for compliance
4. **Secure Permissions**: Regularly verify file permissions haven't changed
5. **Document Changes**: Update this policy when retention requirements change
6. **Audit Access**: Monitor who accesses log files
7. **Encrypt at Rest**: Consider encrypting log files for sensitive data
8. **Centralized Logging**: Consider using log aggregation tools (ELK, Splunk, etc.)

## References

- Requirements: 9.4, 9.5, 9.6, 9.9
- Design Document: `.kiro/specs/app-modernization-and-enhancement/design.md`
- Logging Documentation: `docs/LOGGING.md`
- Flask Logging Config: `face_recognition_app/flask_api/logging_config.py`
- Next.js Logger: `face_recognition_app/nextjs_backend/lib/logger.ts`

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-04-30 | 1.0 | Initial policy document | System |

