"""
Test for Task 2.7: Timeline generation from detection data

This test verifies that the get_timeline() method correctly:
1. Groups consecutive detections by person
2. Creates timeline entries for continuous appearance segments
3. Splits entries when person disappears for at least one frame
4. Calculates start_time, end_time, detection_count, avg_confidence correctly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'face_recognition_app', 'flask_api'))

from face_recognition_app.flask_api.services.video_processor import VideoProcessorService
from face_recognition_app.flask_api.db import queries
from face_recognition_app.database.db_connection import DatabaseConnection
from config import config
import urllib.parse


def get_test_db_connection():
    """Create a database connection for testing."""
    parsed = urllib.parse.urlparse(config.DATABASE_URL)
    return DatabaseConnection(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        database=(parsed.path or "/face_recognition").lstrip("/"),
        user=parsed.username or "admin",
        password=parsed.password or "admin",
    )


def setup_test_data(db):
    """
    Create test video and detections for timeline generation testing.
    
    Test scenario:
    - Video ID: test video
    - Person A: frames 0-5 (continuous), frames 10-12 (continuous after gap)
    - Person B: frames 2-4 (continuous)
    - Unknown: frames 7-8 (continuous)
    
    Expected timeline entries:
    - Person A: 2 entries (frames 0-5, frames 10-12)
    - Person B: 1 entry (frames 2-4)
    - Unknown: 1 entry (frames 7-8)
    """
    # Insert test video
    video_id = queries.insert_video(
        db,
        filename="test_timeline.mp4",
        file_path="/tmp/test_timeline.mp4",
        file_size_bytes=1000000,
        video_hash="test_timeline_hash_123",
        duration_seconds=15.0,
        fps=1.0,
        width=1920,
        height=1080,
    )
    
    # Insert test person
    person_a_id = queries.upsert_person(db, "Person A")
    person_b_id = queries.upsert_person(db, "Person B")
    
    # Insert detections for Person A (frames 0-5, continuous)
    for frame_num in range(6):
        queries.insert_video_detection(
            db,
            video_id=video_id,
            frame_number=frame_num,
            timestamp=float(frame_num),
            person_id=person_a_id,
            person_name="Person A",
            bbox_x1=100,
            bbox_y1=100,
            bbox_x2=200,
            bbox_y2=200,
            recognition_confidence=0.85 + frame_num * 0.01,  # Varying confidence
            detection_confidence=0.95,
            is_unknown=False,
        )
    
    # Insert detections for Person B (frames 2-4, continuous)
    for frame_num in range(2, 5):
        queries.insert_video_detection(
            db,
            video_id=video_id,
            frame_number=frame_num,
            timestamp=float(frame_num),
            person_id=person_b_id,
            person_name="Person B",
            bbox_x1=300,
            bbox_y1=100,
            bbox_x2=400,
            bbox_y2=200,
            recognition_confidence=0.75,
            detection_confidence=0.92,
            is_unknown=False,
        )
    
    # Insert detections for Unknown (frames 7-8, continuous)
    for frame_num in range(7, 9):
        queries.insert_video_detection(
            db,
            video_id=video_id,
            frame_number=frame_num,
            timestamp=float(frame_num),
            person_id=None,
            person_name="Unknown",
            bbox_x1=500,
            bbox_y1=100,
            bbox_x2=600,
            bbox_y2=200,
            recognition_confidence=0.35,
            detection_confidence=0.88,
            is_unknown=True,
        )
    
    # Insert detections for Person A (frames 10-12, continuous after gap)
    for frame_num in range(10, 13):
        queries.insert_video_detection(
            db,
            video_id=video_id,
            frame_number=frame_num,
            timestamp=float(frame_num),
            person_id=person_a_id,
            person_name="Person A",
            bbox_x1=100,
            bbox_y1=100,
            bbox_x2=200,
            bbox_y2=200,
            recognition_confidence=0.90,
            detection_confidence=0.95,
            is_unknown=False,
        )
    
    return video_id, person_a_id, person_b_id


def test_timeline_generation():
    """Test the get_timeline() method."""
    print("=" * 80)
    print("Testing Task 2.7: Timeline generation from detection data")
    print("=" * 80)
    
    # Setup
    db = get_test_db_connection()
    service = VideoProcessorService(db)
    
    # Clean up any existing test data first
    print("\n0. Cleaning up any existing test data...")
    db_conn = db.get_connection()
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM videos WHERE video_hash = 'test_timeline_hash_123'")
    db_conn.commit()
    cursor.close()
    db.return_connection(db_conn)
    print("   ✓ Existing test data cleaned up")
    
    # Create test data
    print("\n1. Setting up test data...")
    video_id, person_a_id, person_b_id = setup_test_data(db)
    print(f"   Created test video ID: {video_id}")
    print(f"   Created Person A ID: {person_a_id}")
    print(f"   Created Person B ID: {person_b_id}")
    
    # Generate timeline
    print("\n2. Generating timeline entries...")
    timeline_entries = service.get_timeline(video_id)
    print(f"   Generated {len(timeline_entries)} timeline entries")
    
    # Verify results
    print("\n3. Verifying timeline entries...")
    
    # Expected: 4 entries total
    # - Person A: 2 entries (frames 0-5, frames 10-12)
    # - Person B: 1 entry (frames 2-4)
    # - Unknown: 1 entry (frames 7-8)
    assert len(timeline_entries) == 4, f"Expected 4 entries, got {len(timeline_entries)}"
    print("   ✓ Correct number of timeline entries (4)")
    
    # Group entries by person
    person_a_entries = [e for e in timeline_entries if e['person_name'] == 'Person A']
    person_b_entries = [e for e in timeline_entries if e['person_name'] == 'Person B']
    unknown_entries = [e for e in timeline_entries if e['person_name'] == 'Unknown']
    
    # Verify Person A has 2 entries (split by gap)
    assert len(person_a_entries) == 2, f"Expected 2 entries for Person A, got {len(person_a_entries)}"
    print("   ✓ Person A has 2 entries (split by gap)")
    
    # Sort Person A entries by start_time
    person_a_entries.sort(key=lambda e: e['start_time'])
    
    # Verify first Person A entry (frames 0-5)
    entry1 = person_a_entries[0]
    assert entry1['start_time'] == 0.0, f"Expected start_time 0.0, got {entry1['start_time']}"
    assert entry1['end_time'] == 5.0, f"Expected end_time 5.0, got {entry1['end_time']}"
    assert entry1['detection_count'] == 6, f"Expected 6 detections, got {entry1['detection_count']}"
    # Average confidence: (0.85 + 0.86 + 0.87 + 0.88 + 0.89 + 0.90) / 6 = 0.875
    expected_avg = (0.85 + 0.86 + 0.87 + 0.88 + 0.89 + 0.90) / 6
    assert abs(entry1['avg_confidence'] - expected_avg) < 0.01, \
        f"Expected avg_confidence ~{expected_avg}, got {entry1['avg_confidence']}"
    print(f"   ✓ Person A entry 1: start={entry1['start_time']}, end={entry1['end_time']}, "
          f"count={entry1['detection_count']}, avg_conf={entry1['avg_confidence']:.3f}")
    
    # Verify second Person A entry (frames 10-12)
    entry2 = person_a_entries[1]
    assert entry2['start_time'] == 10.0, f"Expected start_time 10.0, got {entry2['start_time']}"
    assert entry2['end_time'] == 12.0, f"Expected end_time 12.0, got {entry2['end_time']}"
    assert entry2['detection_count'] == 3, f"Expected 3 detections, got {entry2['detection_count']}"
    assert abs(entry2['avg_confidence'] - 0.90) < 0.01, \
        f"Expected avg_confidence 0.90, got {entry2['avg_confidence']}"
    print(f"   ✓ Person A entry 2: start={entry2['start_time']}, end={entry2['end_time']}, "
          f"count={entry2['detection_count']}, avg_conf={entry2['avg_confidence']:.3f}")
    
    # Verify Person B has 1 entry
    assert len(person_b_entries) == 1, f"Expected 1 entry for Person B, got {len(person_b_entries)}"
    entry3 = person_b_entries[0]
    assert entry3['start_time'] == 2.0, f"Expected start_time 2.0, got {entry3['start_time']}"
    assert entry3['end_time'] == 4.0, f"Expected end_time 4.0, got {entry3['end_time']}"
    assert entry3['detection_count'] == 3, f"Expected 3 detections, got {entry3['detection_count']}"
    assert abs(entry3['avg_confidence'] - 0.75) < 0.01, \
        f"Expected avg_confidence 0.75, got {entry3['avg_confidence']}"
    print(f"   ✓ Person B entry: start={entry3['start_time']}, end={entry3['end_time']}, "
          f"count={entry3['detection_count']}, avg_conf={entry3['avg_confidence']:.3f}")
    
    # Verify Unknown has 1 entry
    assert len(unknown_entries) == 1, f"Expected 1 entry for Unknown, got {len(unknown_entries)}"
    entry4 = unknown_entries[0]
    assert entry4['start_time'] == 7.0, f"Expected start_time 7.0, got {entry4['start_time']}"
    assert entry4['end_time'] == 8.0, f"Expected end_time 8.0, got {entry4['end_time']}"
    assert entry4['detection_count'] == 2, f"Expected 2 detections, got {entry4['detection_count']}"
    assert abs(entry4['avg_confidence'] - 0.35) < 0.01, \
        f"Expected avg_confidence 0.35, got {entry4['avg_confidence']}"
    print(f"   ✓ Unknown entry: start={entry4['start_time']}, end={entry4['end_time']}, "
          f"count={entry4['detection_count']}, avg_conf={entry4['avg_confidence']:.3f}")
    
    # Verify entries are stored in database
    print("\n4. Verifying entries are stored in database...")
    db_entries = queries.get_timeline_entries(db, video_id)
    assert len(db_entries) == 4, f"Expected 4 entries in DB, got {len(db_entries)}"
    print(f"   ✓ All {len(db_entries)} entries stored in database")
    
    # Cleanup
    print("\n5. Cleaning up test data...")
    db_conn = db.get_connection()
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM timeline_entries WHERE video_id = %s", (video_id,))
    cursor.execute("DELETE FROM video_detections WHERE video_id = %s", (video_id,))
    cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
    db_conn.commit()
    cursor.close()
    db.return_connection(db_conn)
    print("   ✓ Test data cleaned up")
    
    print("\n" + "=" * 80)
    print("✓ All tests passed!")
    print("=" * 80)


if __name__ == "__main__":
    test_timeline_generation()
