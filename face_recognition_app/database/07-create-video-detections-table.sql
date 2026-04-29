-- ============================================================================
-- Face Recognition System - Video Detections Table
-- Migration: 07-create-video-detections-table.sql
-- ============================================================================
-- Creates the video_detections table for storing frame-level face detection
-- data for video playback with overlay synchronization.
-- 
-- This table stores detection results for each frame in processed videos,
-- enabling real-time overlay rendering during video playback.
-- ============================================================================

-- ============================================================================
-- TABLE: video_detections
-- Frame-level face detection data for video playback overlay
-- ============================================================================
CREATE TABLE IF NOT EXISTS video_detections (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_number INTEGER NOT NULL,
    timestamp FLOAT NOT NULL,
    person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
    person_name VARCHAR(255),
    bbox_x1 INTEGER NOT NULL,
    bbox_y1 INTEGER NOT NULL,
    bbox_x2 INTEGER NOT NULL,
    bbox_y2 INTEGER NOT NULL,
    recognition_confidence FLOAT NOT NULL,
    detection_confidence FLOAT NOT NULL,
    is_unknown BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE video_detections OWNER TO admin;

COMMENT ON TABLE video_detections IS 'Frame-level face detection data for video playback with overlay synchronization';
COMMENT ON COLUMN video_detections.video_id IS 'Reference to the source video';
COMMENT ON COLUMN video_detections.frame_number IS 'Sequential frame number within the video';
COMMENT ON COLUMN video_detections.timestamp IS 'Timestamp in seconds from video start';
COMMENT ON COLUMN video_detections.person_id IS 'Reference to identified person (NULL if unknown)';
COMMENT ON COLUMN video_detections.person_name IS 'Denormalized person name for performance';
COMMENT ON COLUMN video_detections.bbox_x1 IS 'Bounding box top-left X coordinate';
COMMENT ON COLUMN video_detections.bbox_y1 IS 'Bounding box top-left Y coordinate';
COMMENT ON COLUMN video_detections.bbox_x2 IS 'Bounding box bottom-right X coordinate';
COMMENT ON COLUMN video_detections.bbox_y2 IS 'Bounding box bottom-right Y coordinate';
COMMENT ON COLUMN video_detections.recognition_confidence IS 'Face recognition confidence (0-1)';
COMMENT ON COLUMN video_detections.detection_confidence IS 'Face detection confidence (0-1)';
COMMENT ON COLUMN video_detections.is_unknown IS 'TRUE if recognition_confidence < 0.5';

-- ============================================================================
-- INDEXES
-- Optimized for video playback queries and filtering
-- ============================================================================

-- Composite index for timestamp-based queries during video playback
-- This is the primary query pattern: get detections for video at timestamp
CREATE INDEX IF NOT EXISTS idx_video_detections_video_timestamp 
    ON video_detections (video_id, timestamp);

-- Index on person_id for filtering detections by person
CREATE INDEX IF NOT EXISTS idx_video_detections_person 
    ON video_detections (person_id);

-- Composite index for filtering unknown faces by video
CREATE INDEX IF NOT EXISTS idx_video_detections_unknown 
    ON video_detections (video_id, is_unknown);

-- ============================================================================
-- Verify migration
-- ============================================================================
SELECT 
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename = 'video_detections';

SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'video_detections'
ORDER BY ordinal_position;

SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'video_detections'
ORDER BY indexname;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
