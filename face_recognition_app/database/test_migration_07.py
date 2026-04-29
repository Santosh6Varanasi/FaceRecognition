#!/usr/bin/env python3
"""
Unit tests for migration 07-create-video-detections-table.sql
Tests that the new table, columns, indexes, and constraints exist and work correctly.
"""
import psycopg2
from datetime import datetime

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'database': 'face_recognition',
    'user': 'postgres',
    'password': 'postgres'
}

def test_table_exists():
    """Test that video_detections table exists."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'video_detections'
        );
    """)
    exists = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    assert exists, "video_detections table should exist"
    print("✅ test_table_exists passed")

def test_required_columns():
    """Test that all required columns exist with correct types."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'video_detections'
        ORDER BY ordinal_position;
    """)
    columns = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Check required columns
    required_columns = {
        'id': 'integer',
        'video_id': 'integer',
        'frame_number': 'integer',
        'timestamp': 'double precision',
        'person_id': 'integer',
        'person_name': 'character varying',
        'bbox_x1': 'integer',
        'bbox_y1': 'integer',
        'bbox_x2': 'integer',
        'bbox_y2': 'integer',
        'recognition_confidence': 'double precision',
        'detection_confidence': 'double precision',
        'is_unknown': 'boolean',
        'created_at': 'timestamp without time zone'
    }
    
    for col_name, expected_type in required_columns.items():
        assert col_name in columns, f"Column {col_name} should exist"
        assert columns[col_name] == expected_type, \
            f"Column {col_name} should be {expected_type}, got {columns[col_name]}"
    
    cursor.close()
    conn.close()
    
    print("✅ test_required_columns passed")

def test_indexes_exist():
    """Test that required indexes exist."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'video_detections';
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    
    required_indexes = [
        'idx_video_detections_video_timestamp',
        'idx_video_detections_person',
        'idx_video_detections_unknown'
    ]
    
    for idx_name in required_indexes:
        assert idx_name in indexes, f"Index {idx_name} should exist"
    
    cursor.close()
    conn.close()
    
    print("✅ test_indexes_exist passed")

def test_foreign_key_constraints():
    """Test that foreign key constraints exist."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'video_detections';
    """)
    foreign_keys = cursor.fetchall()
    
    # Check that we have foreign keys
    assert len(foreign_keys) >= 2, "Should have at least 2 foreign key constraints"
    
    # Check specific foreign keys
    fk_dict = {row[0]: (row[1], row[2]) for row in foreign_keys}
    
    assert 'video_id' in fk_dict, "video_id should have foreign key constraint"
    assert fk_dict['video_id'] == ('videos', 'id'), \
        "video_id should reference videos(id)"
    
    assert 'person_id' in fk_dict, "person_id should have foreign key constraint"
    assert fk_dict['person_id'] == ('people', 'id'), \
        "person_id should reference people(id)"
    
    cursor.close()
    conn.close()
    
    print("✅ test_foreign_key_constraints passed")

def test_cascade_delete():
    """Test that CASCADE delete is configured on video_id."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT
            kcu.column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.referential_constraints AS rc
            ON tc.constraint_name = rc.constraint_name
        WHERE tc.table_name = 'video_detections'
            AND tc.constraint_type = 'FOREIGN KEY'
            AND kcu.column_name = 'video_id';
    """)
    result = cursor.fetchone()
    
    assert result is not None, "video_id foreign key should exist"
    assert result[1] == 'CASCADE', "video_id should have CASCADE delete rule"
    
    cursor.close()
    conn.close()
    
    print("✅ test_cascade_delete passed")

def test_insert_and_query():
    """Test inserting and querying detection data."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    try:
        # First, ensure we have a test video
        cursor.execute("""
            INSERT INTO videos (filename, file_path, file_size_bytes, video_hash, status)
            VALUES ('test_video.mp4', '/tmp/test_video.mp4', 1024, 'test_hash_07', 'processed')
            RETURNING id;
        """)
        video_id = cursor.fetchone()[0]
        
        # Insert a test detection
        cursor.execute("""
            INSERT INTO video_detections (
                video_id, frame_number, timestamp, person_name,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                recognition_confidence, detection_confidence, is_unknown
            ) VALUES (
                %s, 1, 0.5, 'Test Person',
                100, 150, 200, 250,
                0.92, 0.98, FALSE
            ) RETURNING id;
        """, (video_id,))
        detection_id = cursor.fetchone()[0]
        
        # Query the detection
        cursor.execute("""
            SELECT video_id, frame_number, timestamp, person_name,
                   recognition_confidence, detection_confidence, is_unknown
            FROM video_detections
            WHERE id = %s;
        """, (detection_id,))
        result = cursor.fetchone()
        
        assert result is not None, "Should retrieve inserted detection"
        assert result[0] == video_id, "video_id should match"
        assert result[1] == 1, "frame_number should be 1"
        assert abs(result[2] - 0.5) < 0.001, "timestamp should be 0.5"
        assert result[3] == 'Test Person', "person_name should match"
        assert abs(result[4] - 0.92) < 0.001, "recognition_confidence should be 0.92"
        assert abs(result[5] - 0.98) < 0.001, "detection_confidence should be 0.98"
        assert result[6] == False, "is_unknown should be False"
        
        # Test timestamp-based query (simulating video playback)
        cursor.execute("""
            SELECT id, person_name
            FROM video_detections
            WHERE video_id = %s
              AND timestamp BETWEEN %s AND %s;
        """, (video_id, 0.25, 0.75))
        results = cursor.fetchall()
        
        assert len(results) == 1, "Should find detection within timestamp range"
        
        # Clean up
        cursor.execute("DELETE FROM videos WHERE id = %s;", (video_id,))
        conn.commit()
        
        print("✅ test_insert_and_query passed")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def test_cascade_delete_behavior():
    """Test that deleting a video cascades to video_detections."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    try:
        # Create a test video
        cursor.execute("""
            INSERT INTO videos (filename, file_path, file_size_bytes, video_hash, status)
            VALUES ('cascade_test.mp4', '/tmp/cascade_test.mp4', 2048, 'cascade_hash_07', 'processed')
            RETURNING id;
        """)
        video_id = cursor.fetchone()[0]
        
        # Insert detections
        cursor.execute("""
            INSERT INTO video_detections (
                video_id, frame_number, timestamp, person_name,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                recognition_confidence, detection_confidence, is_unknown
            ) VALUES 
                (%s, 1, 1.0, 'Person A', 10, 20, 30, 40, 0.9, 0.95, FALSE),
                (%s, 2, 2.0, 'Person B', 50, 60, 70, 80, 0.85, 0.92, FALSE);
        """, (video_id, video_id))
        
        # Verify detections exist
        cursor.execute("""
            SELECT COUNT(*) FROM video_detections WHERE video_id = %s;
        """, (video_id,))
        count_before = cursor.fetchone()[0]
        assert count_before == 2, "Should have 2 detections before delete"
        
        # Delete the video
        cursor.execute("DELETE FROM videos WHERE id = %s;", (video_id,))
        
        # Verify detections were cascaded
        cursor.execute("""
            SELECT COUNT(*) FROM video_detections WHERE video_id = %s;
        """, (video_id,))
        count_after = cursor.fetchone()[0]
        assert count_after == 0, "Detections should be deleted via CASCADE"
        
        conn.commit()
        print("✅ test_cascade_delete_behavior passed")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("RUNNING MIGRATION 07 TESTS")
    print("=" * 80 + "\n")
    
    tests = [
        test_table_exists,
        test_required_columns,
        test_indexes_exist,
        test_foreign_key_constraints,
        test_cascade_delete,
        test_insert_and_query,
        test_cascade_delete_behavior
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 80 + "\n")
    
    return failed == 0

if __name__ == "__main__":
    # Run tests manually without pytest
    print("Running migration tests...")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # Check if table exists before running tests
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'video_detections'
        );
    """)
    table_exists = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    if not table_exists:
        print("⚠️  Table 'video_detections' does not exist.")
        print("   Run the migration first: python run_migration_07.py")
        exit(1)
    
    success = run_all_tests()
    exit(0 if success else 1)
