"""
Unit tests for migration 06-enhance-videos-table.sql
Tests that the new columns and indexes exist and work correctly.
"""
import psycopg2
import pytest
from datetime import datetime

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'face_recognition',
    'user': 'admin',
    'password': 'admin'
}

@pytest.fixture
def db_connection():
    """Create database connection for tests."""
    conn = psycopg2.connect(**DB_PARAMS)
    yield conn
    conn.close()

def test_new_columns_exist(db_connection):
    """Test that all new columns were added to videos table."""
    cursor = db_connection.cursor()
    
    # Check for new columns
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'videos'
          AND column_name IN ('frame_count', 'uploaded_by', 'processed_at', 
                             'reprocessed_at', 'model_version')
        ORDER BY column_name
    """)
    
    columns = [row[0] for row in cursor.fetchall()]
    expected_columns = ['frame_count', 'model_version', 'processed_at', 
                       'reprocessed_at', 'uploaded_by']
    
    assert sorted(columns) == sorted(expected_columns), \
        f"Expected columns {expected_columns}, but found {columns}"
    
    cursor.close()

def test_indexes_exist(db_connection):
    """Test that required indexes were created."""
    cursor = db_connection.cursor()
    
    # Check for indexes
    cursor.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'videos'
          AND indexname IN ('idx_videos_status', 'idx_videos_uploaded_at',
                           'idx_videos_model_version', 'idx_videos_uploaded_by')
        ORDER BY indexname
    """)
    
    indexes = [row[0] for row in cursor.fetchall()]
    expected_indexes = ['idx_videos_model_version', 'idx_videos_status', 
                       'idx_videos_uploaded_at', 'idx_videos_uploaded_by']
    
    assert sorted(indexes) == sorted(expected_indexes), \
        f"Expected indexes {expected_indexes}, but found {indexes}"
    
    cursor.close()

def test_column_data_types(db_connection):
    """Test that new columns have correct data types."""
    cursor = db_connection.cursor()
    
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'videos'
          AND column_name IN ('frame_count', 'uploaded_by', 'processed_at', 
                             'reprocessed_at', 'model_version')
        ORDER BY column_name
    """)
    
    column_types = {row[0]: row[1] for row in cursor.fetchall()}
    
    assert column_types['frame_count'] == 'integer'
    assert column_types['uploaded_by'] == 'integer'
    assert column_types['model_version'] == 'integer'
    assert column_types['processed_at'] == 'timestamp without time zone'
    assert column_types['reprocessed_at'] == 'timestamp without time zone'
    
    cursor.close()

def test_insert_with_new_columns(db_connection):
    """Test that we can insert data using the new columns."""
    cursor = db_connection.cursor()
    
    try:
        # Insert a test video with new columns
        cursor.execute("""
            INSERT INTO videos 
            (filename, file_path, file_size_bytes, video_hash, 
             frame_count, uploaded_by, processed_at, model_version, status)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            'test_video.mp4',
            '/tmp/test_video.mp4',
            1024000,
            'test_hash_' + str(datetime.now().timestamp()),
            120,  # frame_count
            1,    # uploaded_by
            datetime.now(),  # processed_at
            1,    # model_version
            'processed'
        ))
        
        video_id = cursor.fetchone()[0]
        assert video_id is not None, "Failed to insert video with new columns"
        
        # Verify the data was inserted correctly
        cursor.execute("""
            SELECT frame_count, uploaded_by, model_version, status
            FROM videos
            WHERE id = %s
        """, (video_id,))
        
        row = cursor.fetchone()
        assert row[0] == 120, "frame_count not stored correctly"
        assert row[1] == 1, "uploaded_by not stored correctly"
        assert row[2] == 1, "model_version not stored correctly"
        assert row[3] == 'processed', "status not stored correctly"
        
        # Clean up
        cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
        db_connection.commit()
        
    except Exception as e:
        db_connection.rollback()
        raise e
    finally:
        cursor.close()

def test_update_reprocessed_at(db_connection):
    """Test that we can update the reprocessed_at timestamp."""
    cursor = db_connection.cursor()
    
    try:
        # Insert a test video
        cursor.execute("""
            INSERT INTO videos 
            (filename, file_path, file_size_bytes, video_hash, status)
            VALUES 
            (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            'test_reprocess.mp4',
            '/tmp/test_reprocess.mp4',
            1024000,
            'test_hash_reprocess_' + str(datetime.now().timestamp()),
            'processed'
        ))
        
        video_id = cursor.fetchone()[0]
        
        # Update reprocessed_at
        reprocess_time = datetime.now()
        cursor.execute("""
            UPDATE videos
            SET reprocessed_at = %s, model_version = %s
            WHERE id = %s
        """, (reprocess_time, 2, video_id))
        
        # Verify the update
        cursor.execute("""
            SELECT reprocessed_at, model_version
            FROM videos
            WHERE id = %s
        """, (video_id,))
        
        row = cursor.fetchone()
        assert row[0] is not None, "reprocessed_at not updated"
        assert row[1] == 2, "model_version not updated"
        
        # Clean up
        cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
        db_connection.commit()
        
    except Exception as e:
        db_connection.rollback()
        raise e
    finally:
        cursor.close()

if __name__ == "__main__":
    # Run tests manually without pytest
    print("Running migration tests...")
    
    conn = psycopg2.connect(**DB_PARAMS)
    
    try:
        print("✓ Test 1: Checking new columns exist...")
        test_new_columns_exist(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 2: Checking indexes exist...")
        test_indexes_exist(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 3: Checking column data types...")
        test_column_data_types(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 4: Testing insert with new columns...")
        test_insert_with_new_columns(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 5: Testing reprocessed_at update...")
        test_update_reprocessed_at(conn)
        print("  ✅ PASSED")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"  ❌ FAILED: {e}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
    finally:
        conn.close()
