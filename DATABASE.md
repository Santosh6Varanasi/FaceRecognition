# Database Documentation

## 📊 Database Overview

The Face Recognition Application uses PostgreSQL as its primary database. This document provides comprehensive information about the database schema, relationships, and management.

## 🗄️ Database Schema

### Tables Overview

| Table | Purpose | Row Estimate |
|-------|---------|--------------|
| people | Store unique person identities | 100-1000 |
| labeled_faces | Training data for face recognition | 1000-10000 |
| unknown_faces | Unrecognized faces awaiting labeling | 100-5000 |
| videos | Video metadata and processing status | 10-1000 |
| video_detections | Frame-by-frame detection results | 10000-1000000 |
| timeline_entries | Aggregated person appearances | 1000-100000 |
| model_versions | Trained model metadata | 10-100 |
| retraining_jobs | Async training job tracking | 10-1000 |

## 📋 Detailed Table Schemas

### 1. people

Stores unique person identities recognized by the system.

```sql
CREATE TABLE people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `name`: Unique person name (e.g., "John Doe")
- `created_at`: Timestamp when person was added

**Indexes:**
```sql
CREATE INDEX idx_people_name ON people(name);
```

**Sample Data:**
```sql
INSERT INTO people (name) VALUES 
    ('John Doe'),
    ('Jane Smith'),
    ('Bob Johnson');
```

### 2. labeled_faces

Training data for the face recognition model.

```sql
CREATE TABLE labeled_faces (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    image_path VARCHAR(512) NOT NULL,
    embedding BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `person_id`: Foreign key to people table
- `image_path`: File system path to face image
- `embedding`: 128-dimensional face encoding (binary)
- `created_at`: Timestamp when face was labeled

**Indexes:**
```sql
CREATE INDEX idx_labeled_faces_person_id ON labeled_faces(person_id);
CREATE INDEX idx_labeled_faces_created_at ON labeled_faces(created_at);
```

**Relationships:**
- Many-to-one with `people` (one person can have many labeled faces)

### 3. unknown_faces

Faces detected but not yet recognized or labeled.

```sql
CREATE TABLE unknown_faces (
    id SERIAL PRIMARY KEY,
    image_path VARCHAR(512) NOT NULL,
    embedding BYTEA NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    source_video_id INTEGER,
    frame_timestamp FLOAT,
    frame_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `image_path`: File system path to face image
- `embedding`: 128-dimensional face encoding (binary)
- `status`: Current status (pending, labeled, rejected)
- `source_video_id`: Optional reference to source video
- `frame_timestamp`: Timestamp in video where face appeared
- `frame_number`: Frame number in video
- `created_at`: Timestamp when face was detected
- `updated_at`: Timestamp of last status change

**Indexes:**
```sql
CREATE INDEX idx_unknown_faces_status ON unknown_faces(status);
CREATE INDEX idx_unknown_faces_source_video_id ON unknown_faces(source_video_id);
CREATE INDEX idx_unknown_faces_created_at ON unknown_faces(created_at);
```

**Status Values:**
- `pending`: Awaiting user action
- `labeled`: User has labeled this face
- `rejected`: User has rejected this face

### 4. videos

Metadata for uploaded and processed videos.

```sql
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(512) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_hash VARCHAR(64) UNIQUE,
    duration FLOAT,
    frame_count INTEGER,
    fps FLOAT,
    width INTEGER,
    height INTEGER,
    uploaded_by VARCHAR(255),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    reprocessed_at TIMESTAMP,
    model_version INTEGER,
    status VARCHAR(50) DEFAULT 'uploaded'
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `filename`: Original filename
- `file_path`: File system path to video
- `file_hash`: SHA-256 hash for duplicate detection
- `duration`: Video duration in seconds
- `frame_count`: Total number of frames
- `fps`: Frames per second
- `width`: Video width in pixels
- `height`: Video height in pixels
- `uploaded_by`: User who uploaded (future auth)
- `uploaded_at`: Upload timestamp
- `processed_at`: When processing completed
- `reprocessed_at`: When last reprocessed
- `model_version`: Model version used for processing
- `status`: Current processing status

**Indexes:**
```sql
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_uploaded_at ON videos(uploaded_at);
CREATE INDEX idx_videos_file_hash ON videos(file_hash);
```

**Status Values:**
- `uploaded`: Video uploaded, not yet processed
- `processing`: Currently being processed
- `completed`: Processing finished successfully
- `failed`: Processing failed
- `reprocessing`: Being reprocessed with new model

### 5. video_detections

Frame-by-frame face detection results.

```sql
CREATE TABLE video_detections (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_number INTEGER NOT NULL,
    timestamp FLOAT NOT NULL,
    person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
    person_name VARCHAR(255),
    bbox_x1 FLOAT NOT NULL,
    bbox_y1 FLOAT NOT NULL,
    bbox_x2 FLOAT NOT NULL,
    bbox_y2 FLOAT NOT NULL,
    recognition_confidence FLOAT,
    detection_confidence FLOAT,
    is_unknown BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `video_id`: Foreign key to videos table
- `frame_number`: Frame number in video
- `timestamp`: Time in seconds from video start
- `person_id`: Foreign key to people (if recognized)
- `person_name`: Person name (denormalized for performance)
- `bbox_x1, bbox_y1, bbox_x2, bbox_y2`: Bounding box coordinates
- `recognition_confidence`: Confidence score (0-1)
- `detection_confidence`: Face detection confidence
- `is_unknown`: True if face not recognized
- `created_at`: Detection timestamp

**Indexes:**
```sql
CREATE INDEX idx_video_detections_video_id ON video_detections(video_id);
CREATE INDEX idx_video_detections_timestamp ON video_detections(video_id, timestamp);
CREATE INDEX idx_video_detections_person_id ON video_detections(person_id);
CREATE INDEX idx_video_detections_is_unknown ON video_detections(video_id, is_unknown);
```

**Relationships:**
- Many-to-one with `videos`
- Many-to-one with `people` (optional)

### 6. timeline_entries

Aggregated view of person appearances in videos.

```sql
CREATE TABLE timeline_entries (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
    person_name VARCHAR(255),
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    detection_count INTEGER DEFAULT 0,
    avg_confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `video_id`: Foreign key to videos table
- `person_id`: Foreign key to people
- `person_name`: Person name (denormalized)
- `start_time`: Start of appearance (seconds)
- `end_time`: End of appearance (seconds)
- `detection_count`: Number of detections in this segment
- `avg_confidence`: Average recognition confidence
- `created_at`: Entry creation timestamp

**Indexes:**
```sql
CREATE INDEX idx_timeline_entries_video_id ON timeline_entries(video_id);
CREATE INDEX idx_timeline_entries_person_id ON timeline_entries(person_id);
```

**Relationships:**
- Many-to-one with `videos`
- Many-to-one with `people` (optional)

### 7. model_versions

Metadata for trained face recognition models.

```sql
CREATE TABLE model_versions (
    version_number SERIAL PRIMARY KEY,
    num_classes INTEGER NOT NULL,
    num_training_samples INTEGER NOT NULL,
    cross_validation_accuracy FLOAT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `version_number`: Auto-incrementing version number
- `num_classes`: Number of people in training set
- `num_training_samples`: Total training samples
- `cross_validation_accuracy`: CV accuracy (0-1)
- `is_active`: Whether this is the active model
- `trained_at`: Training completion timestamp

**Indexes:**
```sql
CREATE INDEX idx_model_versions_is_active ON model_versions(is_active);
CREATE INDEX idx_model_versions_trained_at ON model_versions(trained_at);
```

**Constraints:**
- Only one model can be active at a time

### 8. retraining_jobs

Tracks asynchronous model retraining jobs.

```sql
CREATE TABLE retraining_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'pending',
    progress_pct INTEGER DEFAULT 0,
    message TEXT,
    version_number INTEGER,
    cv_accuracy FLOAT,
    num_classes INTEGER,
    num_training_samples INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `job_id`: Unique job identifier (UUID)
- `status`: Current job status
- `progress_pct`: Progress percentage (0-100)
- `message`: Status message
- `version_number`: Resulting model version (when complete)
- `cv_accuracy`: Cross-validation accuracy
- `num_classes`: Number of classes trained
- `num_training_samples`: Total samples used
- `created_at`: Job creation timestamp
- `updated_at`: Last update timestamp

**Indexes:**
```sql
CREATE INDEX idx_retraining_jobs_status ON retraining_jobs(status);
CREATE INDEX idx_retraining_jobs_created_at ON retraining_jobs(created_at);
```

**Status Values:**
- `pending`: Job queued
- `running`: Currently training
- `completed`: Training successful
- `failed`: Training failed

## 🔗 Relationships Diagram

```
people (1) ──────< (M) labeled_faces
  │
  │
  └──────< (M) video_detections
              │
              └──────> (1) videos
                          │
                          └──────< (M) timeline_entries
                          │
                          └──────< (M) video_detections

unknown_faces ──────> (0..1) videos (optional)

model_versions (independent)
retraining_jobs (independent)
```

## 📊 Common Queries

### Get All People with Face Count

```sql
SELECT 
    p.id,
    p.name,
    COUNT(lf.id) as face_count,
    p.created_at
FROM people p
LEFT JOIN labeled_faces lf ON p.id = lf.person_id
GROUP BY p.id, p.name, p.created_at
ORDER BY face_count DESC;
```

### Get Video Processing Statistics

```sql
SELECT 
    status,
    COUNT(*) as count,
    AVG(duration) as avg_duration,
    SUM(frame_count) as total_frames
FROM videos
GROUP BY status;
```

### Get Unknown Faces by Status

```sql
SELECT 
    status,
    COUNT(*) as count,
    MIN(created_at) as oldest,
    MAX(created_at) as newest
FROM unknown_faces
GROUP BY status;
```

### Get Detections for Video at Timestamp

```sql
SELECT 
    person_name,
    bbox_x1, bbox_y1, bbox_x2, bbox_y2,
    recognition_confidence,
    timestamp
FROM video_detections
WHERE video_id = $1
  AND ABS(timestamp - $2) <= $3
ORDER BY timestamp;
```

### Get Timeline for Video

```sql
SELECT 
    person_name,
    start_time,
    end_time,
    detection_count,
    avg_confidence
FROM timeline_entries
WHERE video_id = $1
ORDER BY start_time;
```

### Get Active Model Version

```sql
SELECT 
    version_number,
    num_classes,
    num_training_samples,
    cross_validation_accuracy,
    trained_at
FROM model_versions
WHERE is_active = TRUE
LIMIT 1;
```

## 🔧 Maintenance Queries

### Vacuum and Analyze

```sql
-- Reclaim storage and update statistics
VACUUM ANALYZE videos;
VACUUM ANALYZE video_detections;
VACUUM ANALYZE unknown_faces;
VACUUM ANALYZE labeled_faces;
```

### Check Table Sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Index Usage

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Find Unused Indexes

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexname NOT LIKE '%_pkey';
```

### Check Slow Queries

```sql
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## 🗑️ Data Cleanup

### Delete Old Unknown Faces

```sql
-- Delete rejected faces older than 30 days
DELETE FROM unknown_faces
WHERE status = 'rejected'
  AND updated_at < NOW() - INTERVAL '30 days';
```

### Archive Old Videos

```sql
-- Move old processed videos to archive table
INSERT INTO videos_archive
SELECT * FROM videos
WHERE status = 'completed'
  AND processed_at < NOW() - INTERVAL '90 days';

DELETE FROM videos
WHERE status = 'completed'
  AND processed_at < NOW() - INTERVAL '90 days';
```

### Clean Up Failed Jobs

```sql
-- Delete failed retraining jobs older than 7 days
DELETE FROM retraining_jobs
WHERE status = 'failed'
  AND created_at < NOW() - INTERVAL '7 days';
```

## 📈 Performance Optimization

### Add Missing Indexes

```sql
-- If queries are slow, add these indexes
CREATE INDEX CONCURRENTLY idx_video_detections_frame_number 
ON video_detections(video_id, frame_number);

CREATE INDEX CONCURRENTLY idx_unknown_faces_status_created 
ON unknown_faces(status, created_at DESC);

CREATE INDEX CONCURRENTLY idx_timeline_entries_person_video 
ON timeline_entries(person_id, video_id);
```

### Partition Large Tables

```sql
-- Partition video_detections by video_id (for very large datasets)
CREATE TABLE video_detections_partitioned (
    LIKE video_detections INCLUDING ALL
) PARTITION BY HASH (video_id);

CREATE TABLE video_detections_p0 PARTITION OF video_detections_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE video_detections_p1 PARTITION OF video_detections_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE video_detections_p2 PARTITION OF video_detections_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE video_detections_p3 PARTITION OF video_detections_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

## 🔒 Security

### Create Read-Only User

```sql
-- Create read-only user for reporting
CREATE USER face_recognition_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE face_recognition TO face_recognition_readonly;
GRANT USAGE ON SCHEMA public TO face_recognition_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO face_recognition_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO face_recognition_readonly;
```

### Revoke Dangerous Permissions

```sql
-- Ensure application user cannot drop tables
REVOKE DROP ON ALL TABLES IN SCHEMA public FROM face_recognition_user;
```

## 💾 Backup and Restore

### Full Database Backup

```bash
# Backup entire database
pg_dump -U postgres -d face_recognition > backup_full_$(date +%Y%m%d).sql

# Backup with compression
pg_dump -U postgres -d face_recognition | gzip > backup_full_$(date +%Y%m%d).sql.gz
```

### Table-Specific Backup

```bash
# Backup specific tables
pg_dump -U postgres -d face_recognition -t people -t labeled_faces > backup_training_data.sql
```

### Restore Database

```bash
# Restore from backup
psql -U postgres -d face_recognition < backup_full_20260429.sql

# Restore from compressed backup
gunzip -c backup_full_20260429.sql.gz | psql -U postgres -d face_recognition
```

## 📊 Monitoring

### Connection Count

```sql
SELECT count(*) FROM pg_stat_activity;
```

### Active Queries

```sql
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query,
    query_start
FROM pg_stat_activity
WHERE state = 'active'
  AND query NOT LIKE '%pg_stat_activity%';
```

### Database Size

```sql
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
ORDER BY pg_database_size(pg_database.datname) DESC;
```

### Lock Monitoring

```sql
SELECT 
    locktype,
    relation::regclass,
    mode,
    granted,
    pid
FROM pg_locks
WHERE NOT granted;
```

## 🔄 Migration Scripts

All migration scripts are located in `face_recognition_app/database/`:

1. `CLEANUP_ALL.sql` - Drop all tables
2. `CREATE_ALL_FRESH.sql` - Create all tables from scratch
3. `01-05-*.sql` - Individual migration scripts (if needed)

To apply migrations:

```bash
# Clean database
psql -U postgres -d face_recognition -f CLEANUP_ALL.sql

# Create fresh schema
psql -U postgres -d face_recognition -f CREATE_ALL_FRESH.sql
```

## 📝 Best Practices

1. **Always use transactions** for multi-step operations
2. **Use prepared statements** to prevent SQL injection
3. **Index foreign keys** for join performance
4. **Regularly vacuum** large tables
5. **Monitor slow queries** and add indexes as needed
6. **Backup before migrations** or major changes
7. **Use connection pooling** in application
8. **Set appropriate timeouts** for long-running queries
9. **Archive old data** to keep tables manageable
10. **Test queries** on development database first
