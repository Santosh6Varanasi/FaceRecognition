-- ============================================================================
-- Face Recognition System - Enhanced Video Processing Migration
-- Migration: 09-extend-unknown-faces-table.sql
-- ============================================================================
-- Extends the unknown_faces table with video source tracking fields:
-- - source_video_id: Links unknown face to source video
-- - frame_timestamp: Timestamp within video where face was detected
-- - frame_number: Frame number within video where face was detected
-- ============================================================================

-- ============================================================================
-- EXTEND TABLE: unknown_faces
-- Add video source tracking columns
-- ============================================================================

-- Add source_video_id column to link unknown face to source video
ALTER TABLE unknown_faces ADD COLUMN IF NOT EXISTS source_video_id INTEGER;
COMMENT ON COLUMN unknown_faces.source_video_id IS 'Foreign key to videos table - source video where this face was detected';

-- Add frame_timestamp column to track when in the video the face appeared
ALTER TABLE unknown_faces ADD COLUMN IF NOT EXISTS frame_timestamp FLOAT;
COMMENT ON COLUMN unknown_faces.frame_timestamp IS 'Timestamp in seconds from video start where face was detected';

-- Add frame_number column to track which frame the face appeared in
ALTER TABLE unknown_faces ADD COLUMN IF NOT EXISTS frame_number INTEGER;
COMMENT ON COLUMN unknown_faces.frame_number IS 'Frame number within the video where face was detected';

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS
-- Add foreign key constraint to videos table
-- ============================================================================

-- Add foreign key constraint to videos table (SET NULL on delete)
-- This allows unknown faces to persist even if source video is deleted
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_unknown_faces_source_video'
          AND table_name = 'unknown_faces'
    ) THEN
        ALTER TABLE unknown_faces
        ADD CONSTRAINT fk_unknown_faces_source_video
        FOREIGN KEY (source_video_id)
        REFERENCES videos(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================================
-- INDEXES
-- Add indexes for performance on source_video_id and status columns
-- ============================================================================

-- Index on source_video_id for filtering unknown faces by source video
CREATE INDEX IF NOT EXISTS idx_unknown_faces_source_video ON unknown_faces (source_video_id);

-- Note: idx_unknown_faces_status already exists from previous migrations
-- Verify it exists for bulk operations
CREATE INDEX IF NOT EXISTS idx_unknown_faces_status ON unknown_faces (status);

-- ============================================================================
-- Verify migration
-- ============================================================================
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'unknown_faces'
  AND column_name IN ('source_video_id', 'frame_timestamp', 'frame_number')
ORDER BY column_name;

SELECT 
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'unknown_faces'
  AND constraint_name = 'fk_unknown_faces_source_video';

SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'unknown_faces'
  AND indexname IN ('idx_unknown_faces_source_video', 'idx_unknown_faces_status')
ORDER BY indexname;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
