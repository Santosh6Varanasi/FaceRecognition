#!/usr/bin/env python3
"""
Unit tests for migration 08-create-timeline-entries-table.sql
Tests that the new table, columns, indexes, and constraints exist and work correctly.
"""
import psycopg2
from datetime import datetime

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'database': 'face_recognition',
    'user': 'admin',
    'password': 'admin'
}

def test_table_exists():
    """Test that timeline_entries table exists."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'timeline_entries'
        );
    """)
    exists = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    assert exists, "timeline_entries table should exist"
    print("✅ test_table_exists passed")

def test_required_columns():
    """Test that all required columns exist with correct types."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'timeline_entries'
        ORDER BY ordinal_position;
    """)
    columns = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Check required columns
    required_columns = {
        'id': 'integer',
        'video_id': 'integer',
        'person_id': 'integer',
        'person_name': 'character varying',
        'start_time': 'double precision',
        'end_time': 'double precision',
        'detection_count': 'integer',
        'avg_confidence': 'double precision',
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
        WHERE tablename = 'timeline_entries';
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    
    required_indexes = [
        'idx_timeline_video',
        'idx_timeline_person'
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
            AND tc.table_name = 'timeline_entries';
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
        WHERE tc.table_name = 'timeline_entries'
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
    """Test inserting and querying timeline entry data."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    try:
        # First, ensure we have a test video
        cursor.execute("""
            INSERT INTO videos (filename, file_path, file_size_bytes, video_hash, status)
            VALUES ('test_timeline.mp4', '/tmp/test_timeline.mp4', 1024, 'test_hash_08', 'processed')
            RETURNING id;
        """)
        video_id = cursor.fetchone()[0]
        
        # Insert a test timeline entry
        cursor.execute("""
            INSERT INTO timeline_entries (
                video_id, person_name, start_time, end_time,
                detection_count, avg_confidence
            ) VALUES (
                %s, 'Test Person', 10.5, 45.2, 35, 0.89
            ) RETURNING id;
        """, (video_id,))
        entry_id = cursor.fetchone()[0]
        
        # Query the timeline entry
        cursor.execute("""
            SELECT video_id, person_name, start_time, end_time,
                   detection_count, avg_confidence
            FROM timeline_entries
            WHERE id = %s;
        """, (entry_id,))
        result = cursor.fetchone()
        
        assert result is not None, "Should retrieve inserted timeline entry"
        assert result[0] == video_id, "video_id should match"
        assert result[1] == 'Test Person', "person_name should match"
        assert abs(result[2] - 10.5) < 0.001, "start_time should be 10.5"
        assert abs(result[3] - 45.2) < 0.001, "end_time should be 45.2"
        assert result[4] == 35, "detection_count should be 35"
        assert abs(result[5] - 0.89) < 0.001, "avg_confidence should be 0.89"
        
        # Test querying all entries for a video
        cursor.execute("""
            SELECT id, person_name, start_time, end_time
            FROM timeline_entries
            WHERE video_id = %s
            ORDER BY start_time;
        """, (video_id,))
        results = cursor.fetchall()
        
        assert len(results) == 1, "Should find one timeline entry for video"
        
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
    """Test that deleting a video cascades to timeline_entries."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    try:
        # Create a test video
        cursor.execute("""
            INSERT INTO videos (filename, file_path, file_size_bytes, video_hash, status)
            VALUES ('cascade_timeline.mp4', '/tmp/cascade_timeline.mp4', 2048, 'cascade_hash_08', 'processed')
            RETURNING id;
        """)
        video_id = cursor.fetchone()[0]
        
        # Insert timeline entries
        cursor.execute("""
            INSERT INTO timeline_entries (
                video_id, person_name, start_time, end_time,
                detection_count, avg_confidence
            ) VALUES 
                (%s, 'Person A', 0.0, 30.0, 30, 0.92),
                (%s, 'Person B', 35.0, 60.0, 25, 0.88);
        """, (video_id, video_id))
        
        # Verify entries exist
        cursor.execute("""
            SELECT COUNT(*) FROM timeline_entries WHERE video_id = %s;
        """, (video_id,))
        count_before = cursor.fetchone()[0]
        assert count_before == 2, "Should have 2 timeline entries before delete"
        
        # Delete the video
        cursor.execute("DELETE FROM videos WHERE id = %s;", (video_id,))
        
        # Verify entries were cascaded
        cursor.execute("""
            SELECT COUNT(*) FROM timeline_entries WHERE video_id = %s;
        """, (video_id,))
        count_after = cursor.fetchone()[0]
        assert count_after == 0, "Timeline entries should be deleted via CASCADE"
        
        conn.commit()
        print("✅ test_cascade_delete_behavior passed")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def test_multiple_entries_per_person():
    """Test that multiple timeline entries can exist for the same person (non-consecutive appearances)."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    try:
        # Create a test video
        cursor.execute("""
            INSERT INTO videos (filename, file_path, file_size_bytes, video_hash, status)
            VALUES ('multi_entry.mp4', '/tmp/multi_entry.mp4', 3072, 'multi_hash_08', 'processed')
            RETURNING id;
        """)
        video_id = cursor.fetchone()[0]
        
        # Insert multiple entries for the same person (non-consecutive appearances)
        cursor.execute("""
            INSERT INTO timeline_entries (
                video_id, person_name, start_time, end_time,
                detection_count, avg_confidence
            ) VALUES 
                (%s, 'John Doe', 0.0, 15.0, 15, 0.90),
                (%s, 'John Doe', 30.0, 45.0, 15, 0.88),
                (%s, 'John Doe', 60.0, 75.0, 15, 0.92);
        """, (video_id, video_id, video_id))
        
        # Query entries for this person
        cursor.execute("""
            SELECT COUNT(*), person_name
            FROM timeline_entries
            WHERE video_id = %s AND person_name = 'John Doe'
            GROUP BY person_name;
        """, (video_id,))
        result = cursor.fetchone()
        
        assert result is not None, "Should find entries for John Doe"
        assert result[0] == 3, "Should have 3 separate timeline entries for John Doe"
        
        # Clean up
        cursor.execute("DELETE FROM videos WHERE id = %s;", (video_id,))
        conn.commit()
        
        print("✅ test_multiple_entries_per_person passed")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("RUNNING MIGRATION 08 TESTS")
    print("=" * 80 + "\n")
    
    tests = [
        test_table_exists,
        test_required_columns,
        test_indexes_exist,
        test_foreign_key_constraints,
        test_cascade_delete,
        test_insert_and_query,
        test_cascade_delete_behavior,
        test_multiple_entries_per_person
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
            AND table_name = 'timeline_entries'
        );
    """)
    table_exists = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    if not table_exists:
        print("⚠️  Table 'timeline_entries' does not exist.")
        print("   Run the migration first: python run_migration_08.py")
        exit(1)
    
    success = run_all_tests()
    exit(0 if success else 1)
