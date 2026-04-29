-- ============================================================================
-- Face Recognition System - Sample Data for Testing
-- ============================================================================
-- This script populates the database with sample data for development/testing
-- DO NOT RUN in production - use only for testing the schema
-- ============================================================================

-- ============================================================================
-- INSERT SAMPLE PEOPLE
-- ============================================================================
INSERT INTO people (name, description, role) VALUES
    ('Alice Johnson', 'Team Lead, Engineering', 'employee'),
    ('Bob Smith', 'Senior Developer', 'employee'),
    ('Charlie Brown', 'Security Officer', 'employee'),
    ('Diana Prince', 'Product Manager', 'employee'),
    ('Eve Wilson', 'Data Scientist', 'employee')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- INSERT SAMPLE EMBEDDINGS (PLACEHOLDER)
-- ============================================================================
-- Create random sample embeddings for testing
-- In production, these will be real ArcFace embeddings
-- Each person gets 5 sample training faces

INSERT INTO faces (person_id, image_path, embedding, face_confidence, source_type)
SELECT 
    p.id,
    CONCAT('/training_data/', p.name, '/image_', seq.idx, '.jpg'),
    -- Create random normalized vectors (placeholder - replace with real ArcFace embeddings)
    ARRAY(SELECT RANDOM()::float8 FROM GENERATE_SERIES(1, 512))::vector(512),
    0.95,
    'training'
FROM people p
CROSS JOIN LATERAL GENERATE_SERIES(1, 5) AS seq(idx)
ON CONFLICT (person_id, image_path) DO NOTHING;

-- ============================================================================
-- INSERT SAMPLE VIDEO SESSION
-- ============================================================================
INSERT INTO video_sessions (session_name, camera_source, notes)
VALUES (
    'Test Session - April 25 2026',
    'browser_webcam',
    'Sample session for development testing'
)
ON CONFLICT DO NOTHING;

-- Get the session ID for reference
-- SELECT id FROM video_sessions WHERE session_name = 'Test Session - April 25 2026' LIMIT 1;

-- ============================================================================
-- INSERT SAMPLE FRAMES (only if session exists)
-- ============================================================================
INSERT INTO frames (video_session_id, frame_number, image_path, width, height, processing_time_ms)
SELECT 
    vs.id,
    seq.frame_num,
    CONCAT('/frames/session_', vs.id, '_frame_', seq.frame_num, '.jpg'),
    1920,
    1080,
    45.2
FROM video_sessions vs
CROSS JOIN LATERAL GENERATE_SERIES(1, 10) AS seq(frame_num)
WHERE vs.session_name = 'Test Session - April 25 2026'
ON CONFLICT (video_session_id, frame_number) DO NOTHING;

-- ============================================================================
-- INSERT SAMPLE DETECTIONS (only if frames exist)
-- ============================================================================
INSERT INTO detections (frame_id, person_id, embedding, detection_bbox_x1, detection_bbox_y1, 
                       detection_bbox_x2, detection_bbox_y2, detection_confidence, 
                       svm_prediction, svm_probability, is_correct)
SELECT 
    f.id,
    (ARRAY[1, 2, 3, 4, 5])[((f.id - 1) % 5) + 1], -- Cycle through first 5 persons
    ARRAY(SELECT RANDOM()::float8 FROM GENERATE_SERIES(1, 512))::vector(512),
    100 + RANDOM()::int * 1000,  -- Random X1
    100 + RANDOM()::int * 800,   -- Random Y1
    200 + RANDOM()::int * 1000,  -- Random X2
    200 + RANDOM()::int * 800,   -- Random Y2
    0.90 + RANDOM() * 0.09,
    p.name,
    0.85 + RANDOM() * 0.14,
    TRUE
FROM frames f
JOIN people p ON p.id = (ARRAY[1, 2, 3, 4, 5])[((f.id - 1) % 5) + 1]
WHERE f.video_session_id = (SELECT id FROM video_sessions WHERE session_name = 'Test Session - April 25 2026' LIMIT 1)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- INSERT SAMPLE UNKNOWN FACES
-- ============================================================================
INSERT INTO unknown_faces (embedding, source_image_path, detection_confidence, 
                          svm_prediction, svm_probability, status)
VALUES 
    (ARRAY(SELECT RANDOM()::float8 FROM GENERATE_SERIES(1, 512))::vector(512), 
     '/unknown/unknown_1.jpg', 0.88, 'Unknown', 0.45, 'pending'),
    (ARRAY(SELECT RANDOM()::float8 FROM GENERATE_SERIES(1, 512))::vector(512), 
     '/unknown/unknown_2.jpg', 0.92, 'Alice Johnson', 0.48, 'pending'),
    (ARRAY(SELECT RANDOM()::float8 FROM GENERATE_SERIES(1, 512))::vector(512), 
     '/unknown/unknown_3.jpg', 0.85, 'Bob Smith', 0.42, 'reviewed'),
    (ARRAY(SELECT RANDOM()::float8 FROM GENERATE_SERIES(1, 512))::vector(512), 
     '/unknown/unknown_4.jpg', 0.91, 'Charlie Brown', 0.49, 'pending')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- INSERT SAMPLE MODEL VERSION
-- ============================================================================
-- Create a placeholder SVM model (in production, this will be joblib-serialized)
INSERT INTO model_versions (version_number, model_bytes, label_encoder_bytes, num_classes, 
                           num_training_samples, trained_at, training_duration_seconds,
                           cross_validation_accuracy, cross_validation_std,
                           per_class_accuracy, svm_hyperparams, is_active)
VALUES (
    1,
    E'\\x00\\x01\\x02\\x03'::bytea,  -- Placeholder model bytes
    E'\\x00\\x01\\x02\\x03'::bytea,  -- Placeholder label encoder bytes
    5,  -- 5 persons
    25, -- 5 images × 5 persons
    CURRENT_TIMESTAMP,
    2.5,
    0.92,  -- 92% accuracy
    0.04,  -- ±4% std
    '{"Alice Johnson": 0.95, "Bob Smith": 0.88, "Charlie Brown": 0.92, "Diana Prince": 0.90, "Eve Wilson": 0.93}'::jsonb,
    '{"C": 10.0, "gamma": "scale", "kernel": "rbf"}'::jsonb,
    TRUE
)
ON CONFLICT (version_number) DO NOTHING;

-- ============================================================================
-- VERIFY DATA INSERTED
-- ============================================================================
SELECT '====== DATA VERIFICATION ======' as status;

SELECT 'People count: ' || COUNT(*) FROM people;
SELECT 'Faces count: ' || COUNT(*) FROM faces;
SELECT 'Unknown faces count: ' || COUNT(*) FROM unknown_faces;
SELECT 'Video sessions count: ' || COUNT(*) FROM video_sessions;
SELECT 'Frames count: ' || COUNT(*) FROM frames;
SELECT 'Detections count: ' || COUNT(*) FROM detections;
SELECT 'Model versions count: ' || COUNT(*) FROM model_versions;

-- Sample queries
SELECT 'Top 3 persons by face count:';
SELECT p.name, COUNT(f.id) as face_count
FROM people p
LEFT JOIN faces f ON p.id = f.person_id
GROUP BY p.id, p.name
ORDER BY face_count DESC
LIMIT 3;

SELECT 'Unknown faces by status:';
SELECT status, COUNT(*) as count
FROM unknown_faces
GROUP BY status;

-- ============================================================================
-- END OF SAMPLE DATA SCRIPT
-- ============================================================================
