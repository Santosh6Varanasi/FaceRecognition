-- ============================================================================
-- COMPLETE DATABASE CREATION SCRIPT
-- ============================================================================
-- Purpose: Create all tables, indexes, and constraints from scratch
-- Usage: Run this after CLEANUP_ALL.sql for a fresh database
-- ============================================================================

-- ============================================================================
-- 1. PEOPLE TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_people_name ON people(name);

-- ============================================================================
-- 2. LABELED FACES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS labeled_faces (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    image_path VARCHAR(512) NOT NULL,
    embedding BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_labeled_faces_person_id ON labeled_faces(person_id);
CREATE INDEX idx_labeled_faces_created_at ON labeled_faces(created_at);

-- ============================================================================
-- 3. UNKNOWN FACES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS unknown_faces (
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

CREATE INDEX idx_unknown_faces_status ON unknown_faces(status);
CREATE INDEX idx_unknown_faces_source_video_id ON unknown_faces(source_video_id);
CREATE INDEX idx_unknown_faces_created_at ON unknown_faces(created_at);

-- ============================================================================
-- 4. MODEL VERSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_versions (
    version_number SERIAL PRIMARY KEY,
    num_classes INTEGER NOT NULL,
    num_training_samples INTEGER NOT NULL,
    cross_validation_accuracy FLOAT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_versions_is_active ON model_versions(is_active);
CREATE INDEX idx_model_versions_trained_at ON model_versions(trained_at);

-- ============================================================================
-- 5. RETRAINING JOBS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS retraining_jobs (
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

CREATE INDEX idx_retraining_jobs_status ON retraining_jobs(status);
CREATE INDEX idx_retraining_jobs_created_at ON retraining_jobs(created_at);

-- ============================================================================
-- 6. VIDEOS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS videos (
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

CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_uploaded_at ON videos(uploaded_at);
CREATE INDEX idx_videos_file_hash ON videos(file_hash);

-- ============================================================================
-- 7. VIDEO DETECTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS video_detections (
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

CREATE INDEX idx_video_detections_video_id ON video_detections(video_id);
CREATE INDEX idx_video_detections_timestamp ON video_detections(video_id, timestamp);
CREATE INDEX idx_video_detections_person_id ON video_detections(person_id);
CREATE INDEX idx_video_detections_is_unknown ON video_detections(video_id, is_unknown);

-- ============================================================================
-- 8. TIMELINE ENTRIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS timeline_entries (
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

CREATE INDEX idx_timeline_entries_video_id ON timeline_entries(video_id);
CREATE INDEX idx_timeline_entries_person_id ON timeline_entries(person_id);

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 
    'Database created successfully' AS status,
    COUNT(*) AS table_count
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';

-- List all created tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;
