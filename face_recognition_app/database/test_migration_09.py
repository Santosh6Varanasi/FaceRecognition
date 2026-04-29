"""
Unit tests for migration 09-extend-unknown-faces-table.sql
Tests that the new columns, indexes, and foreign key constraints exist and work correctly.
"""
import psycopg2
import pytest
import numpy as np
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
    """Test that all new columns were added to unknown_faces table."""
    cursor = db_connection.cursor()
    
    # Check for new columns
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'unknown_faces'
          AND column_name IN ('source_video_id', 'frame_timestamp', 'frame_number')
        ORDER BY column_name
    """)
    
    columns = [row[0] for row in cursor.fetchall()]
    expected_columns = ['frame_number', 'frame_timestamp', 'source_video_id']
    
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
        WHERE tablename = 'unknown_faces'
          AND indexname IN ('idx_unknown_faces_source_video', 'idx_unknown_faces_status')
        ORDER BY indexname
    """)
    
    indexes = [row[0] for row in cursor.fetchall()]
    expected_indexes = ['idx_unknown_faces_source_video', 'idx_unknown_faces_status']
    
    assert sorted(indexes) == sorted(expected_indexes), \
        f"Expected indexes {expected_indexes}, but found {indexes}"
    
    cursor.close()

def test_foreign_key_constraint_exists(db_connection):
    """Test that foreign key constraint to videos table was created."""
    cursor = db_connection.cursor()
    
    cursor.execute("""
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_name = 'unknown_faces'
          AND constraint_name = 'fk_unknown_faces_source_video'
    """)
    
    result = cursor.fetchone()
    assert result is not None, "Foreign key constraint not found"
    assert result[1] == 'FOREIGN KEY', f"Expected FOREIGN KEY constraint, got {result[1]}"
    
    cursor.close()

def test_column_data_types(db_connection):
    """Test that new columns have correct data types."""
    cursor = db_connection.cursor()
    
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'unknown_faces'
          AND column_name IN ('source_video_id', 'frame_timestamp', 'frame_number')
        ORDER BY column_name
    """)
    
    column_types = {row[0]: row[1] for row in cursor.fetchall()}
    
    assert column_types['source_video_id'] == 'integer'
    assert column_types['frame_timestamp'] == 'double precision'
    assert column_types['frame_number'] == 'integer'
    
    cursor.close()

def test_insert_with_new_columns(db_connection):
    """Test that we can insert unknown faces with video source tracking."""
    cursor = db_connection.cursor()
    
    try:
        # First, create a test video
        cursor.execute("""
            INSERT INTO videos 
            (filename, file_path, file_size_bytes, video_hash, status)
            VALUES 
            (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            'test_video_unknown.mp4',
            '/tmp/test_video_unknown.mp4',
            1024000,
            'test_hash_unknown_' + str(datetime.now().timestamp()),
            'processed'
        ))
        
        video_id = cursor.fetchone()[0]
        
        # Create a dummy embedding (512-dimensional vector)
        embedding = np.random.rand(512).tolist()
        
        # Insert an unknown face with video source tracking
        cursor.execute("""
            INSERT INTO unknown_faces 
            (embedding, source_image_path, source_video_id, frame_timestamp, 
             frame_number, detection_confidence, svm_probability, status)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            embedding,
            '/tmp/unknown_face.jpg',
            video_id,
            45.5,  # frame_timestamp
            91,    # frame_number (assuming 2 fps: 45.5 * 2 = 91)
            0.95,  # detection_confidence
            0.42,  # svm_probability (below threshold)
            'pending'
        ))
        
        face_id = cursor.fetchone()[0]
        assert face_id is not None, "Failed to insert unknown face with new columns"
        
        # Verify the data was inserted correctly
        cursor.execute("""
            SELECT source_video_id, frame_timestamp, frame_number, status
            FROM unknown_faces
            WHERE id = %s
        """, (face_id,))
        
        row = cursor.fetchone()
        assert row[0] == video_id, "source_video_id not stored correctly"
        assert abs(row[1] - 45.5) < 0.01, "frame_timestamp not stored correctly"
        assert row[2] == 91, "frame_number not stored correctly"
        assert row[3] == 'pending', "status not stored correctly"
        
        # Clean up
        cursor.execute("DELETE FROM unknown_faces WHERE id = %s", (face_id,))
        cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
        db_connection.commit()
        
    except Exception as e:
        db_connection.rollback()
        raise e
    finally:
        cursor.close()

def test_foreign_key_cascade_behavior(db_connection):
    """Test that deleting a video sets source_video_id to NULL (ON DELETE SET NULL)."""
    cursor = db_connection.cursor()
    
    try:
        # Create a test video
        cursor.execute("""
            INSERT INTO videos 
            (filename, file_path, file_size_bytes, video_hash, status)
            VALUES 
            (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            'test_video_cascade.mp4',
            '/tmp/test_video_cascade.mp4',
            1024000,
            'test_hash_cascade_' + str(datetime.now().timestamp()),
            'processed'
        ))
        
        video_id = cursor.fetchone()[0]
        
        # Create a dummy embedding
        embedding = np.random.rand(512).tolist()
        
        # Insert an unknown face linked to this video
        cursor.execute("""
            INSERT INTO unknown_faces 
            (embedding, source_video_id, frame_timestamp, frame_number, status)
            VALUES 
            (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            embedding,
            video_id,
            30.0,
            60,
            'pending'
        ))
        
        face_id = cursor.fetchone()[0]
        
        # Verify the link exists
        cursor.execute("""
            SELECT source_video_id
            FROM unknown_faces
            WHERE id = %s
        """, (face_id,))
        
        assert cursor.fetchone()[0] == video_id, "source_video_id not linked correctly"
        
        # Delete the video
        cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
        
        # Verify that source_video_id is now NULL (ON DELETE SET NULL)
        cursor.execute("""
            SELECT source_video_id
            FROM unknown_faces
            WHERE id = %s
        """, (face_id,))
        
        result = cursor.fetchone()[0]
        assert result is None, f"Expected source_video_id to be NULL after video deletion, got {result}"
        
        # Clean up
        cursor.execute("DELETE FROM unknown_faces WHERE id = %s", (face_id,))
        db_connection.commit()
        
    except Exception as e:
        db_connection.rollback()
        raise e
    finally:
        cursor.close()

def test_query_unknown_faces_by_video(db_connection):
    """Test that we can efficiently query unknown faces by source video."""
    cursor = db_connection.cursor()
    
    try:
        # Create a test video
        cursor.execute("""
            INSERT INTO videos 
            (filename, file_path, file_size_bytes, video_hash, status)
            VALUES 
            (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            'test_video_query.mp4',
            '/tmp/test_video_query.mp4',
            1024000,
            'test_hash_query_' + str(datetime.now().timestamp()),
            'processed'
        ))
        
        video_id = cursor.fetchone()[0]
        
        # Insert multiple unknown faces from this video
        face_ids = []
        for i in range(3):
            embedding = np.random.rand(512).tolist()
            cursor.execute("""
                INSERT INTO unknown_faces 
                (embedding, source_video_id, frame_timestamp, frame_number, status)
                VALUES 
                (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                embedding,
                video_id,
                float(i * 10),
                i * 20,
                'pending'
            ))
            face_ids.append(cursor.fetchone()[0])
        
        # Query unknown faces by video
        cursor.execute("""
            SELECT id, frame_timestamp, frame_number
            FROM unknown_faces
            WHERE source_video_id = %s
            ORDER BY frame_timestamp
        """, (video_id,))
        
        results = cursor.fetchall()
        assert len(results) == 3, f"Expected 3 unknown faces, found {len(results)}"
        
        # Verify ordering by frame_timestamp
        for i, row in enumerate(results):
            assert abs(row[1] - (i * 10)) < 0.01, f"Expected frame_timestamp {i * 10}, got {row[1]}"
            assert row[2] == i * 20, f"Expected frame_number {i * 20}, got {row[2]}"
        
        # Clean up
        for face_id in face_ids:
            cursor.execute("DELETE FROM unknown_faces WHERE id = %s", (face_id,))
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
        
        print("✓ Test 3: Checking foreign key constraint exists...")
        test_foreign_key_constraint_exists(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 4: Checking column data types...")
        test_column_data_types(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 5: Testing insert with new columns...")
        test_insert_with_new_columns(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 6: Testing foreign key cascade behavior...")
        test_foreign_key_cascade_behavior(conn)
        print("  ✅ PASSED")
        
        print("✓ Test 7: Testing query unknown faces by video...")
        test_query_unknown_faces_by_video(conn)
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
