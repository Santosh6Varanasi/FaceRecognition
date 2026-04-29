-- ============================================================================
-- Face Recognition System - Video Processing Tables
-- Migration: 05-video-tables.sql
-- ============================================================================
-- Adds video upload, async job tracking, and frame timestamp support.
-- Run AFTER 02-create-tables.sql (depends on video_sessions, frames).
-- ============================================================================

-- ============================================================================
-- EXTEND TABLE: frames
-- Add timestamp_ms for video playback synchronization
-- ============================================================================
ALTER TABLE frames ADD COLUMN IF NOT EXISTS timestamp_ms BIGINT;

COMMENT ON COLUMN frames.timestamp_ms IS
    'Offset in milliseconds from video start (NULL for live camera frames)';

-- ============================================================================
-- TABLE: videos
-- Uploaded video files with hash-based deduplication
-- ============================================================================
CREATE TABLE IF NOT EXISTS videos (
    id                  SERIAL PRIMARY KEY,
    filename            VARCHAR(512) NOT NULL,
    file_path           VARCHAR(512) NOT NULL,
    file_size_bytes     BIGINT NOT NULL,
    video_hash          VARCHAR(64) NOT NULL UNIQUE,
    duration_seconds    FLOAT,
    fps                 FLOAT,
    width               INT,
    height              INT,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    uploaded_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_processed_at   TIMESTAMP,
    unique_unknowns     INT NOT NULL DEFAULT 0,
    unique_known        INT NOT NULL DEFAULT 0
);

ALTER TABLE videos OWNER TO admin;
COMMENT ON TABLE videos IS 'Uploaded video files tracked by SHA-256 hash for deduplication';
COMMENT ON COLUMN videos.video_hash IS 'SHA-256 hex digest of raw file bytes — used for re-upload detection';
COMMENT ON COLUMN videos.status IS 'pending: uploaded | processing: job running | processed: complete | failed: error';
COMMENT ON COLUMN videos.unique_unknowns IS 'Count of unique unknown faces found in most recent processing run';
COMMENT ON COLUMN videos.unique_known IS 'Count of unique known persons identified in most recent processing run';

-- ============================================================================
-- TABLE: video_jobs
-- Async processing jobs — one per processing run per video
-- ============================================================================
CREATE TABLE IF NOT EXISTS video_jobs (
    id                  SERIAL PRIMARY KEY,
    job_id              VARCHAR(64) NOT NULL UNIQUE,
    video_id            INT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    video_session_id    UUID REFERENCES video_sessions(id) ON DELETE SET NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'queued'
                            CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    progress_pct        INT NOT NULL DEFAULT 0,
    frames_processed    INT NOT NULL DEFAULT 0,
    total_frames        INT NOT NULL DEFAULT 0,
    message             TEXT,
    unique_unknowns     INT NOT NULL DEFAULT 0,
    unique_known        INT NOT NULL DEFAULT 0,
    started_at          TIMESTAMP,
    completed_at        TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE video_jobs OWNER TO admin;
COMMENT ON TABLE video_jobs IS 'Async video processing jobs — one row per processing run';
COMMENT ON COLUMN video_jobs.job_id IS 'UUID string used as the public job identifier';
COMMENT ON COLUMN video_jobs.video_session_id IS 'Links to the video_sessions row created for this run';
COMMENT ON COLUMN video_jobs.progress_pct IS 'Integer 0-100: floor(frames_processed / total_frames * 100)';
COMMENT ON COLUMN video_jobs.message IS 'Human-readable status message for UI display';

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_videos_video_hash
    ON videos (video_hash);

CREATE INDEX IF NOT EXISTS idx_video_jobs_video_id
    ON video_jobs (video_id);

CREATE INDEX IF NOT EXISTS idx_video_jobs_job_id
    ON video_jobs (job_id);

CREATE INDEX IF NOT EXISTS idx_video_jobs_status
    ON video_jobs (status);

CREATE INDEX IF NOT EXISTS idx_frames_timestamp_ms
    ON frames (timestamp_ms)
    WHERE timestamp_ms IS NOT NULL;

-- ============================================================================
-- Verify migration
-- ============================================================================
SELECT
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('videos', 'video_jobs')
ORDER BY tablename;

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'frames'
  AND column_name = 'timestamp_ms';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
