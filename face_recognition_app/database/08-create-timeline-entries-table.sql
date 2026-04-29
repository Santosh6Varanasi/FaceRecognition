-- ============================================================================
-- Face Recognition System - Timeline Entries Table
-- Migration: 08-create-timeline-entries-table.sql
-- ============================================================================
-- Creates the timeline_entries table for storing person appearance segments
-- in videos for timeline visualization.
-- 
-- This table stores aggregated timeline segments showing when each person
-- appears in videos, enabling efficient timeline navigation and visualization.
-- ============================================================================

-- ============================================================================
-- TABLE: timeline_entries
-- Person appearance segments for timeline visualization
-- ============================================================================
CREATE TABLE IF NOT EXISTS timeline_entries (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
    person_name VARCHAR(255),
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    detection_count INTEGER NOT NULL,
    avg_confidence FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE timeline_entries OWNER TO admin;

COMMENT ON TABLE timeline_entries IS 'Person appearance segments for timeline visualization';
COMMENT ON COLUMN timeline_entries.video_id IS 'Reference to the source video';
COMMENT ON COLUMN timeline_entries.person_id IS 'Reference to identified person (NULL if unknown)';
COMMENT ON COLUMN timeline_entries.person_name IS 'Denormalized person name for performance';
COMMENT ON COLUMN timeline_entries.start_time IS 'Segment start time in seconds from video start';
COMMENT ON COLUMN timeline_entries.end_time IS 'Segment end time in seconds from video start';
COMMENT ON COLUMN timeline_entries.detection_count IS 'Number of detections in this segment';
COMMENT ON COLUMN timeline_entries.avg_confidence IS 'Average recognition confidence for this segment';

-- ============================================================================
-- INDEXES
-- Optimized for timeline queries and filtering
-- ============================================================================

-- Index on video_id for retrieving all timeline entries for a video
CREATE INDEX IF NOT EXISTS idx_timeline_video 
    ON timeline_entries (video_id);

-- Index on person_id for filtering timeline entries by person
CREATE INDEX IF NOT EXISTS idx_timeline_person 
    ON timeline_entries (person_id);

-- ============================================================================
-- Verify migration
-- ============================================================================
SELECT 
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename = 'timeline_entries';

SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'timeline_entries'
ORDER BY ordinal_position;

SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'timeline_entries'
ORDER BY indexname;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
