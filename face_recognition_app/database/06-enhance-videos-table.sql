-- ============================================================================
-- Face Recognition System - Enhanced Video Processing Migration
-- Migration: 06-enhance-videos-table.sql
-- ============================================================================
-- Enhances the videos table with additional metadata fields for:
-- - Frame count tracking
-- - User attribution (uploaded_by)
-- - Processing timestamps (processed_at, reprocessed_at)
-- - Model version tracking
-- ============================================================================

-- ============================================================================
-- EXTEND TABLE: videos
-- Add missing columns for enhanced video processing UI
-- ============================================================================

-- Add frame_count column to track total frames in video
ALTER TABLE videos ADD COLUMN IF NOT EXISTS frame_count INTEGER;
COMMENT ON COLUMN videos.frame_count IS 'Total number of frames in the video';

-- Add uploaded_by column to track which user uploaded the video
ALTER TABLE videos ADD COLUMN IF NOT EXISTS uploaded_by INTEGER;
COMMENT ON COLUMN videos.uploaded_by IS 'User ID who uploaded the video (references users table if exists)';

-- Add processed_at column for initial processing timestamp
ALTER TABLE videos ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP;
COMMENT ON COLUMN videos.processed_at IS 'Timestamp when video was first successfully processed';

-- Add reprocessed_at column for reprocessing timestamp
ALTER TABLE videos ADD COLUMN IF NOT EXISTS reprocessed_at TIMESTAMP;
COMMENT ON COLUMN videos.reprocessed_at IS 'Timestamp when video was last reprocessed with updated model';

-- Add model_version column to track which model version was used
ALTER TABLE videos ADD COLUMN IF NOT EXISTS model_version INTEGER;
COMMENT ON COLUMN videos.model_version IS 'Model version number used for processing (references model_versions table)';

-- ============================================================================
-- INDEXES
-- Add indexes for performance on status and uploaded_at columns
-- ============================================================================

-- Index on status for filtering videos by processing status
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos (status);

-- Index on uploaded_at for sorting and filtering by upload time
CREATE INDEX IF NOT EXISTS idx_videos_uploaded_at ON videos (uploaded_at);

-- Index on model_version for filtering videos by model version
CREATE INDEX IF NOT EXISTS idx_videos_model_version ON videos (model_version);

-- Index on uploaded_by for filtering videos by user
CREATE INDEX IF NOT EXISTS idx_videos_uploaded_by ON videos (uploaded_by);

-- ============================================================================
-- Verify migration
-- ============================================================================
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'videos'
  AND column_name IN ('frame_count', 'uploaded_by', 'processed_at', 'reprocessed_at', 'model_version')
ORDER BY column_name;

SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'videos'
  AND indexname IN ('idx_videos_status', 'idx_videos_uploaded_at', 'idx_videos_model_version', 'idx_videos_uploaded_by')
ORDER BY indexname;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
