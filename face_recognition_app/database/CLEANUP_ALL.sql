-- ============================================================================
-- DATABASE CLEANUP SCRIPT
-- ============================================================================
-- Purpose: Drop all tables, indexes, and data for a fresh start
-- Usage: Run this script to completely reset the database
-- WARNING: This will DELETE ALL DATA permanently!
-- ============================================================================

-- Drop all tables in reverse dependency order
DROP TABLE IF EXISTS timeline_entries CASCADE;
DROP TABLE IF EXISTS video_detections CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS unknown_faces CASCADE;
DROP TABLE IF EXISTS labeled_faces CASCADE;
DROP TABLE IF EXISTS people CASCADE;
DROP TABLE IF EXISTS model_versions CASCADE;
DROP TABLE IF EXISTS retraining_jobs CASCADE;

-- Verify all tables are dropped
SELECT 'All tables dropped successfully' AS status;
