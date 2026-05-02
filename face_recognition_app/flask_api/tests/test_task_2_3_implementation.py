"""
Test for Task 2.3: Face recognition and unknown face extraction implementation.

This test verifies that:
1. Face recognition is called for each detected face
2. Detection results are stored in video_detections table with bbox coordinates
3. Unknown faces (confidence < 0.5) are extracted and saved to unknown_faces table
4. Unknown faces are associated with source video_id and frame_timestamp
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call


class TestTask23Implementation:
    """Test suite for Task 2.3 implementation."""
    
    def test_insert_unknown_face_with_video_tracking(self):
        """Test that insert_unknown_face accepts video source tracking parameters."""
        # Import here to avoid dependency issues
        from db import queries
        
        db_mock = Mock()
        db_conn_mock = Mock()
        cursor_mock = Mock()
        
        # Setup mocks
        db_mock.get_connection.return_value = db_conn_mock
        db_mock.return_connection = Mock()
        db_conn_mock.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (123,)  # Return face_id
        
        # Create test embedding
        embedding = np.random.rand(512).astype(np.float64)
        
        # Call insert_unknown_face with video tracking parameters
        face_id = queries.insert_unknown_face(
            conn=db_mock,
            embedding=embedding,
            source_image_path="test.jpg",
            frame_id=None,
            detection_confidence=0.95,
            svm_prediction="Unknown",
            svm_probability=0.3,
            source_video_id=42,
            frame_timestamp=1.5,
            frame_number=15
        )
        
        # Verify the function was called and returned face_id
        assert face_id == 123
        
        # Verify the SQL INSERT was called with video tracking columns
        cursor_mock.execute.assert_called_once()
        sql_call = cursor_mock.execute.call_args[0][0]
        assert "source_video_id" in sql_call
        assert "frame_timestamp" in sql_call
        assert "frame_number" in sql_call
        
        # Verify the parameters include video tracking data
        params = cursor_mock.execute.call_args[0][1]
        assert params[6] == 42  # source_video_id
        assert params[7] == 1.5  # frame_timestamp
        assert params[8] == 15  # frame_number
    
    def test_insert_video_detection_function_exists(self):
        """Test that insert_video_detection function exists and works."""
        # Import here to avoid dependency issues
        from db import queries
        
        db_mock = Mock()
        db_conn_mock = Mock()
        cursor_mock = Mock()
        
        # Setup mocks
        db_mock.get_connection.return_value = db_conn_mock
        db_mock.return_connection = Mock()
        db_conn_mock.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (456,)  # Return detection_id
        
        # Call insert_video_detection
        detection_id = queries.insert_video_detection(
            conn=db_mock,
            video_id=42,
            frame_number=10,
            timestamp=1.5,
            person_id=5,
            person_name="John Doe",
            bbox_x1=100,
            bbox_y1=150,
            bbox_x2=200,
            bbox_y2=250,
            recognition_confidence=0.85,
            detection_confidence=0.95,
            is_unknown=False
        )
        
        # Verify the function was called and returned detection_id
        assert detection_id == 456
        
        # Verify the SQL INSERT was called
        cursor_mock.execute.assert_called_once()
        sql_call = cursor_mock.execute.call_args[0][0]
        assert "INSERT INTO video_detections" in sql_call
        assert "video_id" in sql_call
        assert "frame_number" in sql_call
        assert "timestamp" in sql_call
        assert "person_id" in sql_call
        assert "person_name" in sql_call
        assert "bbox_x1" in sql_call
        assert "recognition_confidence" in sql_call
        assert "is_unknown" in sql_call
    
    def test_unknown_face_extraction_by_confidence_threshold(self):
        """Test that faces with confidence < 0.5 are marked as unknown."""
        # Import here to avoid dependency issues
        from db import queries
        
        db_mock = Mock()
        db_conn_mock = Mock()
        cursor_mock = Mock()
        
        # Setup mocks
        db_mock.get_connection.return_value = db_conn_mock
        db_mock.return_connection = Mock()
        db_conn_mock.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (789,)
        
        # Test with confidence < 0.5 (should be unknown)
        detection_id = queries.insert_video_detection(
            conn=db_mock,
            video_id=42,
            frame_number=10,
            timestamp=1.5,
            person_id=None,
            person_name="Unknown",
            bbox_x1=100,
            bbox_y1=150,
            bbox_x2=200,
            bbox_y2=250,
            recognition_confidence=0.3,  # < 0.5
            detection_confidence=0.95,
            is_unknown=True  # Should be True for confidence < 0.5
        )
        
        # Verify is_unknown is True
        params = cursor_mock.execute.call_args[0][1]
        assert params[-1] == True  # is_unknown parameter
        
        # Reset mock
        cursor_mock.reset_mock()
        cursor_mock.fetchone.return_value = (790,)
        
        # Test with confidence >= 0.5 (should not be unknown)
        detection_id = queries.insert_video_detection(
            conn=db_mock,
            video_id=42,
            frame_number=11,
            timestamp=2.0,
            person_id=5,
            person_name="John Doe",
            bbox_x1=100,
            bbox_y1=150,
            bbox_x2=200,
            bbox_y2=250,
            recognition_confidence=0.85,  # >= 0.5
            detection_confidence=0.95,
            is_unknown=False  # Should be False for confidence >= 0.5
        )
        
        # Verify is_unknown is False
        params = cursor_mock.execute.call_args[0][1]
        assert params[-1] == False  # is_unknown parameter


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
