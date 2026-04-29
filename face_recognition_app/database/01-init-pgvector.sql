-- ============================================================================
-- Face Recognition System - Database Initialization
-- PostgreSQL Setup: Create database and enable pgvector extension
-- ============================================================================
-- Run as superuser (postgres) first

-- Create database if not exists
CREATE DATABASE face_recognition WITH
  ENCODING 'UTF8'
  LC_COLLATE 'en_US.UTF-8'
  LC_CTYPE 'en_US.UTF-8'
  TEMPLATE template0;

-- Connect to the new database and enable extensions
-- psql -U postgres -d face_recognition -f 01-init-pgvector.sql

-- Enable pgvector extension (required for embedding storage)
CREATE EXTENSION IF NOT EXISTS pgvector;

-- Enable uuid extension (for video_sessions.id)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions are loaded
SELECT extname, extversion FROM pg_extension 
WHERE extname IN ('vector', 'uuid-ossp')
ORDER BY extname;

-- ============================================================================
-- PostgreSQL Configuration for Face Recognition
-- ============================================================================

-- Increase work_memory for large SVM training on high-dimensional data
-- Adjust based on available RAM (default 4MB, recommend 256MB-1GB for embedding operations)
-- ALTER SYSTEM SET work_memory = '256MB';

-- Enable JIT compilation for vectorized operations (PostgreSQL 11+)
-- ALTER SYSTEM SET jit = on;

-- SELECT pg_reload_conf();

-- ============================================================================
-- END OF INITIALIZATION SCRIPT
-- ============================================================================
