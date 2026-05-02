-- ============================================================================
-- COMPLETE DATABASE RESET SCRIPT
-- ============================================================================
-- WARNING: This script will DELETE ALL DATA and recreate all tables
-- Use this to start the application from scratch
-- ============================================================================

-- Drop all tables in correct order (respecting foreign key constraints)
DROP TABLE IF EXISTS video_detections CASCADE;
DROP TABLE IF EXISTS timeline_entries CASCADE;
DROP TABLE IF EXISTS detections CASCADE;
DROP TABLE IF EXISTS frames CASCADE;
DROP TABLE IF EXISTS video_sessions CASCADE;
DROP TABLE IF EXISTS video_jobs CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS unknown_faces CASCADE;
DROP TABLE IF EXISTS faces CASCADE;
DROP TABLE IF EXISTS people CASCADE;
DROP TABLE IF EXISTS model_versions CASCADE;

-- Drop pgvector extension if exists
DROP EXTENSION IF EXISTS vector CASCADE;

-- ============================================================================
-- RECREATE EXTENSION
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLE 1: people
-- ============================================================================
CREATE TABLE people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    role VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE people OWNER TO admin;
COMMENT ON TABLE people IS 'Core person identities in the face recognition system';

-- ============================================================================
-- TABLE 2: model_versions
-- ============================================================================
CREATE TABLE model_versions (
    id SERIAL PRIMARY KEY,
    version_number INT NOT NULL UNIQUE,
    model_bytes BYTEA NOT NULL,
    label_encoder_bytes BYTEA NOT NULL,
    num_classes INT,
    num_training_samples INT,
    trained_at TIMESTAMP,
    training_duration_seconds FLOAT,
    cross_validation_accuracy FLOAT,
    cross_validation_std FLOAT,
    per_class_accuracy JSONB,
    svm_hyperparams JSONB,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE model_versions OWNER TO admin;
COMMENT ON TABLE model_versions IS 'SVM model training history with accuracy metadata';

-- ============================================================================
-- TABLE 3: faces
-- ============================================================================
CREATE TABLE faces (
    id SERIAL PRIMARY KEY,
    person_id INT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    image_path VARCHAR(512) NOT NULL,
    embedding vector(512) NOT NULL,
    face_confidence FLOAT DEFAULT 1.0,
    source_type VARCHAR(50) NOT NULL 
        CHECK (source_type IN ('training', 'unknown_labeled', 'retraining')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_person_image UNIQUE(person_id, image_path)
);

ALTER TABLE faces OWNER TO admin;
COMMENT ON TABLE faces IS 'All training face embeddings (512-d ArcFace vectors)';

-- ============================================================================
-- TABLE 4: unknown_faces
-- ============================================================================
CREATE TABLE unknown_faces (
    id SERIAL PRIMARY KEY,
    embedding vector(512) NOT NULL,
    source_image_path VARCHAR(512),
    source_frame_id INT,
    detection_confidence FLOAT,
    svm_prediction VARCHAR(255),
    svm_probability FLOAT,
    status VARCHAR(50) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'reviewed', 'labeled', 'rejected')),
    assigned_person_id INT REFERENCES people(id) ON DELETE SET NULL,
    labeled_by_user VARCHAR(255),
    labeled_at TIMESTAMP,
    source_video_id INT,
    frame_timestamp FLOAT,
    frame_number INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE unknown_faces OWNER TO admin;
COMMENT ON TABLE unknown_faces IS 'Unidentified faces awaiting labeling';

-- Add foreign key after frames table is created
-- ALTER TABLE unknown_faces ADD CONSTRAINT fk_source_frame 
--     FOREIGN KEY (source_frame_id) REFERENCES frames(id) ON DELETE SET NULL;

-- ============================================================================
-- TABLE 5: video_sessions
-- ============================================================================
CREATE TABLE video_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_name VARCHAR(255),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    total_frames INT DEFAULT 0,
    camera_source VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE video_sessions OWNER TO admin;
COMMENT ON TABLE video_sessions IS 'Camera/video stream sessions for grouping frames';

-- ============================================================================
-- TABLE 6: frames
-- ============================================================================
CREATE TABLE frames (
    id SERIAL PRIMARY KEY,
    video_session_id UUID NOT NULL REFERENCES video_sessions(id) ON DELETE CASCADE,
    frame_number INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_path VARCHAR(512),
    image_blob BYTEA,
    width INT,
    height INT,
    processing_time_ms FLOAT,
    model_version_id INT REFERENCES model_versions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_session_frame UNIQUE(video_session_id, frame_number)
);

ALTER TABLE frames OWNER TO admin;
COMMENT ON TABLE frames IS 'Individual video frames from camera sessions';

-- ============================================================================
-- TABLE 7: detections
-- ============================================================================
CREATE TABLE detections (
    id SERIAL PRIMARY KEY,
    frame_id INT NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    person_id INT REFERENCES people(id) ON DELETE SET NULL,
    unknown_face_id INT REFERENCES unknown_faces(id) ON DELETE SET NULL,
    embedding vector(512),
    detection_bbox_x1 INT,
    detection_bbox_y1 INT,
    detection_bbox_x2 INT,
    detection_bbox_y2 INT,
    detection_confidence FLOAT,
    svm_prediction VARCHAR(255),
    svm_probability FLOAT,
    is_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE detections OWNER TO admin;
COMMENT ON TABLE detections IS 'Individual face detections in frames with identification results';
COMMENT ON COLUMN detections.embedding IS 'Optional embedding vector - primarily stored in faces/unknown_faces tables';

-- ============================================================================
-- TABLE 8: videos
-- ============================================================================
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(512) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size_bytes BIGINT,
    video_hash VARCHAR(64),
    duration_seconds FLOAT,
    fps FLOAT,
    width INT,
    height INT,
    status VARCHAR(50) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_processed_at TIMESTAMP,
    unique_unknowns INT DEFAULT 0,
    unique_known INT DEFAULT 0,
    annotated_video_path VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE videos OWNER TO admin;
COMMENT ON TABLE videos IS 'Uploaded videos for processing';
COMMENT ON COLUMN videos.annotated_video_path IS 'Path to video with bounding boxes burned in';

-- ============================================================================
-- TABLE 9: video_jobs
-- ============================================================================
CREATE TABLE video_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL UNIQUE,
    video_id INT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued' 
        CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    progress_pct INT DEFAULT 0,
    frames_processed INT DEFAULT 0,
    total_frames INT DEFAULT 0,
    message TEXT,
    unique_unknowns INT DEFAULT 0,
    unique_known INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE video_jobs OWNER TO admin;
COMMENT ON TABLE video_jobs IS 'Video processing job status tracking';

-- ============================================================================
-- TABLE 10: video_detections
-- ============================================================================
CREATE TABLE video_detections (
    id SERIAL PRIMARY KEY,
    video_id INT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_number INT NOT NULL,
    timestamp FLOAT NOT NULL,
    person_id INT REFERENCES people(id) ON DELETE SET NULL,
    person_name VARCHAR(255),
    bbox_x1 INT NOT NULL,
    bbox_y1 INT NOT NULL,
    bbox_x2 INT NOT NULL,
    bbox_y2 INT NOT NULL,
    recognition_confidence FLOAT,
    detection_confidence FLOAT,
    is_unknown BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE video_detections OWNER TO admin;
COMMENT ON TABLE video_detections IS 'Face detections in uploaded videos';

-- ============================================================================
-- TABLE 11: timeline_entries
-- ============================================================================
CREATE TABLE timeline_entries (
    id SERIAL PRIMARY KEY,
    video_id INT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    person_id INT REFERENCES people(id) ON DELETE SET NULL,
    person_name VARCHAR(255),
    first_appearance_time FLOAT NOT NULL,
    last_appearance_time FLOAT NOT NULL,
    total_detections INT DEFAULT 0,
    is_unknown BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE timeline_entries OWNER TO admin;
COMMENT ON TABLE timeline_entries IS 'Timeline of person appearances in videos';

-- ============================================================================
-- CREATE INDEXES
-- ============================================================================

-- People indexes
CREATE INDEX idx_people_name ON people(name);

-- Faces indexes
CREATE INDEX idx_faces_person_id ON faces(person_id);
CREATE INDEX idx_faces_source_type ON faces(source_type);

-- Unknown faces indexes
CREATE INDEX idx_unknown_faces_status ON unknown_faces(status);
CREATE INDEX idx_unknown_faces_person_id ON unknown_faces(assigned_person_id);
CREATE INDEX idx_unknown_faces_video_id ON unknown_faces(source_video_id);

-- Frames indexes
CREATE INDEX idx_frames_session_id ON frames(video_session_id);
CREATE INDEX idx_frames_timestamp ON frames(timestamp);

-- Detections indexes
CREATE INDEX idx_detections_frame_id ON detections(frame_id);
CREATE INDEX idx_detections_person_id ON detections(person_id);
CREATE INDEX idx_detections_unknown_face_id ON detections(unknown_face_id);

-- Videos indexes
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_hash ON videos(video_hash);
CREATE INDEX idx_videos_uploaded_at ON videos(uploaded_at);
CREATE INDEX idx_videos_annotated_path ON videos(annotated_video_path);

-- Video jobs indexes
CREATE INDEX idx_video_jobs_job_id ON video_jobs(job_id);
CREATE INDEX idx_video_jobs_video_id ON video_jobs(video_id);
CREATE INDEX idx_video_jobs_status ON video_jobs(status);

-- Video detections indexes
CREATE INDEX idx_video_detections_video_id ON video_detections(video_id);
CREATE INDEX idx_video_detections_person_id ON video_detections(person_id);
CREATE INDEX idx_video_detections_frame_number ON video_detections(frame_number);
CREATE INDEX idx_video_detections_timestamp ON video_detections(timestamp);

-- Timeline entries indexes
CREATE INDEX idx_timeline_entries_video_id ON timeline_entries(video_id);
CREATE INDEX idx_timeline_entries_person_id ON timeline_entries(person_id);

-- Model versions indexes
CREATE INDEX idx_model_versions_active ON model_versions(is_active);
CREATE INDEX idx_model_versions_version_number ON model_versions(version_number);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- ============================================================================
-- END OF RESET SCRIPT
-- ============================================================================
