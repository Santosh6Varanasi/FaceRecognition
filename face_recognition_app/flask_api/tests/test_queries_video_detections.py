"""
Unit tests for video detection query functions.
Tests the get_detections_at_timestamp query function.
"""

import os
import sys
import pytest
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import queries


class TestVideoDetectionQueries:
    """Test suite for video detection query functions."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_db_conn = Mock()
        mock_cursor = Mock()
        
        # Setup connection chain
        mock_conn.get_connection.return_value = mock_db_conn
        mock_db_conn.cursor.return_value = mock_cursor
        
        # Setup return_connection
        mock_conn.return_connection = Mock()
        
        return mock_conn, mock_db_conn, mock_cursor
    
    def test_get_detections_at_timestamp_with_results(self, mock_db_connection):
        """Test get_detections_at_timestamp returns detections within tolerance."""
        mock_conn, mock_db_conn, mock_cursor = mock_db_connection
        
        # Mock database results
        mock_cursor.fetchall.return_value = [
            (1, 'John Doe', 100, 150, 200, 250, 0.92, 0.98),
            (None, 'Unknown', 300, 180, 400, 280, 0.35, 0.95)
        ]
        
        # Call function
        results = queries.get_detections_at_timestamp(
            mock_conn,
            video_id=123,
            timestamp=45.2,
            tolerance=0.25
        )
        
        # Verify query was executed with correct parameters
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'video_detections' in call_args[0][0]
        assert 'ABS(timestamp - %s) <= %s' in call_args[0][0]
        assert call_args[0][1] == (123, 45.2, 0.25)
        
        # Verify results
        assert len(results) == 2
        
        # First detection (known person)
        assert results[0]['person_id'] == 1
        assert results[0]['person_name'] == 'John Doe'
        assert results[0]['bbox'] == {'x1': 100, 'y1': 150, 'x2': 200, 'y2': 250}
        assert results[0]['recognition_confidence'] == 0.92
        assert results[0]['detection_confidence'] == 0.98
        
        # Second detection (unknown person)
        assert results[1]['person_id'] is None
        assert results[1]['person_name'] == 'Unknown'
        assert results[1]['bbox'] == {'x1': 300, 'y1': 180, 'x2': 400, 'y2': 280}
        assert results[1]['recognition_confidence'] == 0.35
        assert results[1]['detection_confidence'] == 0.95
        
        # Verify cleanup
        mock_cursor.close.assert_called_once()
        mock_conn.return_connection.assert_called_once_with(mock_db_conn)
    
    def test_get_detections_at_timestamp_empty_result(self, mock_db_connection):
        """Test get_detections_at_timestamp returns empty list when no detections found."""
        mock_conn, mock_db_conn, mock_cursor = mock_db_connection
        
        # Mock empty database results
        mock_cursor.fetchall.return_value = []
        
        # Call function
        results = queries.get_detections_at_timestamp(
            mock_conn,
            video_id=123,
            timestamp=100.0,
            tolerance=0.25
        )
        
        # Verify empty list returned
        assert results == []
        assert isinstance(results, list)
        
        # Verify cleanup
        mock_cursor.close.assert_called_once()
        mock_conn.return_connection.assert_called_once_with(mock_db_conn)
    
    def test_get_detections_at_timestamp_default_tolerance(self, mock_db_connection):
        """Test get_detections_at_timestamp uses default tolerance of 0.25."""
        mock_conn, mock_db_conn, mock_cursor = mock_db_connection
        
        # Mock database results
        mock_cursor.fetchall.return_value = []
        
        # Call function without tolerance parameter
        queries.get_detections_at_timestamp(
            mock_conn,
            video_id=123,
            timestamp=10.0
        )
        
        # Verify default tolerance was used
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == (123, 10.0, 0.25)
    
    def test_get_detections_at_timestamp_custom_tolerance(self, mock_db_connection):
        """Test get_detections_at_timestamp accepts custom tolerance."""
        mock_conn, mock_db_conn, mock_cursor = mock_db_connection
        
        # Mock database results
        mock_cursor.fetchall.return_value = []
        
        # Call function with custom tolerance
        queries.get_detections_at_timestamp(
            mock_conn,
            video_id=123,
            timestamp=10.0,
            tolerance=0.5
        )
        
        # Verify custom tolerance was used
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == (123, 10.0, 0.5)
    
    def test_get_detections_at_timestamp_null_person_name(self, mock_db_connection):
        """Test get_detections_at_timestamp handles NULL person_name."""
        mock_conn, mock_db_conn, mock_cursor = mock_db_connection
        
        # Mock database results with NULL person_name
        mock_cursor.fetchall.return_value = [
            (None, None, 100, 150, 200, 250, 0.35, 0.98)
        ]
        
        # Call function
        results = queries.get_detections_at_timestamp(
            mock_conn,
            video_id=123,
            timestamp=10.0
        )
        
        # Verify NULL person_name is converted to "Unknown"
        assert results[0]['person_name'] == 'Unknown'
    
    def test_get_detections_at_timestamp_ordered_by_timestamp(self, mock_db_connection):
        """Test get_detections_at_timestamp orders results by timestamp."""
        mock_conn, mock_db_conn, mock_cursor = mock_db_connection
        
        # Mock database results
        mock_cursor.fetchall.return_value = []
        
        # Call function
        queries.get_detections_at_timestamp(
            mock_conn,
            video_id=123,
            timestamp=10.0
        )
        
        # Verify ORDER BY clause is present
        call_args = mock_cursor.execute.call_args
        assert 'ORDER BY timestamp ASC' in call_args[0][0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
