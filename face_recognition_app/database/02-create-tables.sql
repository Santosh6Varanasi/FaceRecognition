-- ============================================================================
-- Face Recognition System - Table Schema
-- PostgreSQL database: face_recognition
-- ============================================================================
-- This script creates all 7 core tables for the face recognition system
-- Embedding dimension: 512 (ArcFace model output)
-- ============================================================================

-- ============================================================================
-- TABLE 1: people
-- Core identities - the persons recognized by the system
-- ============================================================================
CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    role VARCHAR(100),  -- 'employee', 'visitor', 'contractor', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE people OWNER TO admin;
COMMENT ON TABLE people IS 'Core person identities in the face recognition system';
COMMENT ON COLUMN people.name IS 'Unique person name/identifier';
COMMENT ON COLUMN people.role IS 'Role category for access control or analytics';

-- ============================================================================
-- TABLE 2: faces
-- Training faces with ArcFace embeddings (512-dimensional vectors)
-- ============================================================================
CREATE TABLE IF NOT EXISTS faces (
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
COMMENT ON COLUMN faces.person_id IS 'Reference to person identity';
COMMENT ON COLUMN faces.embedding IS 'ArcFace 512-dimensional unit vector';
COMMENT ON COLUMN faces.face_confidence IS 'MTCNN detection confidence (0-1)';
COMMENT ON COLUMN faces.source_type IS 'Origin: training, labeled unknown, or retraining batch';

-- ============================================================================
-- TABLE 3: unknown_faces
-- Detected faces that failed SVM confidence threshold - awaiting labeling
-- ============================================================================
CREATE TABLE IF NOT EXISTS unknown_faces (
    id SERIAL PRIMARY KEY,
    embedding vector(512) NOT NULL,
    source_image_path VARCHAR(512),
    source_frame_id INT REFERENCES frames(id) ON DELETE SET NULL,
    detection_confidence FLOAT,
    svm_prediction VARCHAR(255),
    svm_probability FLOAT,
    status VARCHAR(50) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'reviewed', 'labeled', 'rejected')),
    assigned_person_id INT REFERENCES people(id) ON DELETE SET NULL,
    labeled_by_user VARCHAR(255),
    labeled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE unknown_faces OWNER TO admin;
COMMENT ON TABLE unknown_faces IS 'Unidentified faces awaiting labeling';
COMMENT ON COLUMN unknown_faces.status IS 'pending: not reviewed | reviewed: seen | labeled: assigned person | rejected: false positive';
COMMENT ON COLUMN unknown_faces.svm_probability IS 'SVM confidence in its prediction (may be < threshold)';

-- ============================================================================
-- TABLE 4: video_sessions
-- Track camera/video stream sessions for audit and analytics
-- ============================================================================
CREATE TABLE IF NOT EXISTS video_sessions (
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
COMMENT ON COLUMN video_sessions.camera_source IS 'Source type: browser_webcam, ip_camera, video_file';

-- ============================================================================
-- TABLE 5: frames
-- Individual video frames with processing metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS frames (
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
COMMENT ON COLUMN frames.frame_number IS 'Sequential frame number within session';
COMMENT ON COLUMN frames.processing_time_ms IS 'End-to-end detection + embedding time';
COMMENT ON COLUMN frames.image_blob IS 'Optional compressed frame for replay';

-- ============================================================================
-- TABLE 6: detections
-- Individual face detections per frame with identification results
-- ============================================================================
CREATE TABLE IF NOT EXISTS detections (
    id SERIAL PRIMARY KEY,
    frame_id INT NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    person_id INT REFERENCES people(id) ON DELETE SET NULL,
    unknown_face_id INT REFERENCES unknown_faces(id) ON DELETE SET NULL,
    embedding vector(512) NOT NULL,
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
COMMENT ON COLUMN detections.person_id IS 'NULL if face is unknown (see unknown_face_id)';
COMMENT ON COLUMN detections.unknown_face_id IS 'NULL if face is identified (see person_id)';
COMMENT ON COLUMN detections.is_correct IS 'For ground truth comparison in evaluation';

-- ============================================================================
-- TABLE 7: model_versions
-- SVM model training history with accuracy metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_versions (
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
COMMENT ON COLUMN model_versions.model_bytes IS 'joblib-serialized SVM model';
COMMENT ON COLUMN model_versions.label_encoder_bytes IS 'joblib-serialized LabelEncoder';
COMMENT ON COLUMN model_versions.per_class_accuracy IS 'JSON: {person_name: accuracy_float}';
COMMENT ON COLUMN model_versions.svm_hyperparams IS 'JSON: {C: 10.0, gamma: scale, kernel: rbf}';

-- ============================================================================
-- Verify tables created
-- ============================================================================
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public'
AND tablename IN ('people', 'faces', 'unknown_faces', 'video_sessions', 'frames', 'detections', 'model_versions')
ORDER BY tablename;

-- ============================================================================
-- END OF TABLE CREATION SCRIPT
-- ============================================================================
