-- ============================================================================
-- Face Recognition System - Index Creation
-- PostgreSQL - pgvector indexes for efficient embedding similarity search
-- ============================================================================

-- ============================================================================
-- PEOPLE TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
COMMENT ON INDEX idx_people_name IS 'B-tree index for person lookup by name';

-- ============================================================================
-- FACES TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_faces_person_id ON faces(person_id);
COMMENT ON INDEX idx_faces_person_id IS 'B-tree index for finding all faces of a person';

-- pgvector ivfflat index for L2 distance similarity search
-- lists=100 is recommended for datasets with 100K+ vectors
-- For smaller datasets (<10K), use lists=10
CREATE INDEX IF NOT EXISTS idx_faces_embedding 
    ON faces USING ivfflat (embedding vector_l2_ops) 
    WITH (lists = 100);
COMMENT ON INDEX idx_faces_embedding IS 'pgvector ivfflat index for O(log N) similarity search on embeddings';

-- ============================================================================
-- UNKNOWN_FACES TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_unknown_faces_status ON unknown_faces(status);
COMMENT ON INDEX idx_unknown_faces_status IS 'B-tree index for filtering by labeling status';

CREATE INDEX IF NOT EXISTS idx_unknown_faces_assigned_person ON unknown_faces(assigned_person_id);
COMMENT ON INDEX idx_unknown_faces_assigned_person IS 'B-tree index for finding assigned faces by person';

-- pgvector ivfflat index for finding similar unknown faces
CREATE INDEX IF NOT EXISTS idx_unknown_faces_embedding 
    ON unknown_faces USING ivfflat (embedding vector_l2_ops) 
    WITH (lists = 100);
COMMENT ON INDEX idx_unknown_faces_embedding IS 'pgvector ivfflat index for deduplication of similar unknowns';

-- ============================================================================
-- VIDEO_SESSIONS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_video_sessions_start_time ON video_sessions(start_time);
COMMENT ON INDEX idx_video_sessions_start_time IS 'B-tree index for querying sessions by time range';

-- ============================================================================
-- FRAMES TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_frames_video_session ON frames(video_session_id);
COMMENT ON INDEX idx_frames_video_session IS 'B-tree index for finding all frames in a session';

CREATE INDEX IF NOT EXISTS idx_frames_timestamp ON frames(timestamp);
COMMENT ON INDEX idx_frames_timestamp IS 'B-tree index for querying frames by timestamp';

CREATE INDEX IF NOT EXISTS idx_frames_model_version ON frames(model_version_id);
COMMENT ON INDEX idx_frames_model_version IS 'B-tree index for tracking which model version processed frames';

-- ============================================================================
-- DETECTIONS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_detections_frame_id ON detections(frame_id);
COMMENT ON INDEX idx_detections_frame_id IS 'B-tree index for finding all detections in a frame';

CREATE INDEX IF NOT EXISTS idx_detections_person_id ON detections(person_id);
COMMENT ON INDEX idx_detections_person_id IS 'B-tree index for analytics: detections per person';

CREATE INDEX IF NOT EXISTS idx_detections_unknown_face_id ON detections(unknown_face_id);
COMMENT ON INDEX idx_detections_unknown_face_id IS 'B-tree index for linking detections to unknown faces';

CREATE INDEX IF NOT EXISTS idx_detections_is_correct ON detections(is_correct);
COMMENT ON INDEX idx_detections_is_correct IS 'B-tree index for accuracy evaluation';

-- ============================================================================
-- MODEL_VERSIONS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_model_versions_version_number ON model_versions(version_number);
COMMENT ON INDEX idx_model_versions_version_number IS 'B-tree index for model version lookup';

CREATE INDEX IF NOT EXISTS idx_model_versions_is_active ON model_versions(is_active);
COMMENT ON INDEX idx_model_versions_is_active IS 'B-tree index for finding active model quickly';

-- ============================================================================
-- COMPOSITE INDEXES FOR COMMON QUERIES
-- ============================================================================

-- Query: "Find unknown faces for a specific person after labeling"
CREATE INDEX IF NOT EXISTS idx_unknown_faces_status_person 
    ON unknown_faces(status, assigned_person_id);
COMMENT ON INDEX idx_unknown_faces_status_person IS 'Composite index for labeling workflow queries';

-- Query: "Get accuracy of person X across all detections"
CREATE INDEX IF NOT EXISTS idx_detections_person_correct 
    ON detections(person_id, is_correct);
COMMENT ON INDEX idx_detections_person_correct IS 'Composite index for per-person accuracy calculation';

-- Query: "Find detections in time window for a specific person"
CREATE INDEX IF NOT EXISTS idx_detections_person_created 
    ON detections(person_id, created_at);
COMMENT ON INDEX idx_detections_person_created IS 'Composite index for time-based analytics per person';

-- ============================================================================
-- VERIFY INDEXES
-- ============================================================================
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
AND tablename IN ('people', 'faces', 'unknown_faces', 'video_sessions', 'frames', 'detections', 'model_versions')
ORDER BY tablename, indexname;

-- ============================================================================
-- PGVECTOR INDEX STATISTICS
-- ============================================================================
-- After inserting data, vacuum and analyze indexes:
-- VACUUM ANALYZE faces;
-- VACUUM ANALYZE unknown_faces;
-- VACUUM ANALYZE detections;

-- Check index size:
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_indexes 
-- JOIN pg_class ON pg_class.relname = indexname
-- WHERE schemaname = 'public'
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================================================
-- END OF INDEX CREATION SCRIPT
-- ============================================================================
