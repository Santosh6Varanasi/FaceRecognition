"""
Unit tests for VideoProcessorService class.
Tests video upload handling, format validation, and metadata extraction.
"""

import os
import sys
import pytest
import tempfile
import hashlib
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the inference_service import to avoid dependency issues
sys.modules['services.inference_service'] = Mock()

from services.video_processor import VideoProcessorService, VideoMetadata
from werkzeug.datastructures import FileStorage


class TestVideoProcessorService:
    """Test suite for VideoProcessorService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create VideoProcessorService instance with mock database."""
        return VideoProcessorService(mock_db)
    
    @pytest.fixture
    def temp_video_file(self):
        """Create a temporary video file for testing."""
        # Create a minimal valid video file using OpenCV
        import cv2
        import numpy as np
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_path = temp_file.name
        temp_file.close()
        
        # Create a simple video with a few frames
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, 1.0, (640, 480))
        
        # Write 5 frames
        for i in range(5):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = (i * 50, i * 50, i * 50)  # Gradient
            out.write(frame)
        
        out.release()
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_validate_video_format_valid_mp4(self, service):
        """Test validation accepts valid mp4 format."""
        assert service._validate_video_format('video.mp4') is True
    
    def test_validate_video_format_valid_avi(self, service):
        """Test validation accepts valid avi format."""
        assert service._validate_video_format('video.avi') is True
    
    def test_validate_video_format_valid_mov(self, service):
        """Test validation accepts valid mov format."""
        assert service._validate_video_format('video.mov') is True
    
    def test_validate_video_format_case_insensitive(self, service):
        """Test validation is case insensitive."""
        assert service._validate_video_format('video.MP4') is True
        assert service._validate_video_format('video.AVI') is True
        assert service._validate_video_format('video.MOV') is True
    
    def test_validate_video_format_invalid_extension(self, service):
        """Test validation rejects invalid formats."""
        assert service._validate_video_format('video.mkv') is False
        assert service._validate_video_format('video.wmv') is False
        assert service._validate_video_format('video.flv') is False
    
    def test_validate_video_format_no_extension(self, service):
        """Test validation rejects files without extension."""
        assert service._validate_video_format('video') is False
    
    def test_calculate_file_hash(self, service, temp_video_file):
        """Test file hash calculation."""
        hash1 = service._calculate_file_hash(temp_video_file)
        
        # Hash should be 64 character hex string (SHA-256)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
        
        # Same file should produce same hash
        hash2 = service._calculate_file_hash(temp_video_file)
        assert hash1 == hash2
    
    def test_extract_video_metadata_success(self, service, temp_video_file):
        """Test successful metadata extraction."""
        metadata = service._extract_video_metadata(temp_video_file)
        
        assert 'duration' in metadata
        assert 'fps' in metadata
        assert 'resolution' in metadata
        assert 'frame_count' in metadata
        assert 'width' in metadata
        assert 'height' in metadata
        
        # Check expected values
        assert metadata['fps'] == 1.0
        assert metadata['frame_count'] == 5
        assert metadata['width'] == 640
        assert metadata['height'] == 480
        assert metadata['resolution'] == (640, 480)
        assert metadata['duration'] == 5.0  # 5 frames at 1 fps
    
    def test_extract_video_metadata_invalid_file(self, service):
        """Test metadata extraction fails for invalid file."""
        with pytest.raises(ValueError, match="Cannot open video file"):
            service._extract_video_metadata('/nonexistent/file.mp4')
    
    @patch('services.video_processor.queries')
    def test_upload_video_success(self, mock_queries, service, temp_video_file):
        """Test successful video upload."""
        # Mock database queries
        mock_queries.get_video_by_hash.return_value = None
        mock_queries.insert_video.return_value = 123
        
        # Create mock FileStorage
        with open(temp_video_file, 'rb') as f:
            file_storage = FileStorage(
                stream=f,
                filename='test_video.mp4',
                content_type='video/mp4'
            )
            
            # Upload video
            metadata = service.upload_video(file_storage)
        
        # Verify metadata
        assert isinstance(metadata, VideoMetadata)
        assert metadata.id == 123
        assert metadata.filename == 'test_video.mp4'
        assert metadata.duration == 5.0
        assert metadata.fps == 1.0
        assert metadata.frame_count == 5
        assert metadata.resolution == (640, 480)
        assert metadata.status == 'pending'
        
        # Verify database calls
        mock_queries.get_video_by_hash.assert_called_once()
        mock_queries.insert_video.assert_called_once()
        
        # Cleanup uploaded file
        if os.path.exists(metadata.file_path):
            os.remove(metadata.file_path)
    
    @patch('services.video_processor.queries')
    def test_upload_video_duplicate_detection(self, mock_queries, service, temp_video_file):
        """Test duplicate video detection by hash."""
        # Mock existing video
        existing_video = {
            'id': 456,
            'filename': 'existing_video.mp4',
            'file_path': '/path/to/existing.mp4',
            'duration_seconds': 5.0,
            'fps': 1.0,
            'width': 640,
            'height': 480,
            'uploaded_at': datetime.utcnow(),
            'last_processed_at': None,
            'status': 'pending'
        }
        mock_queries.get_video_by_hash.return_value = existing_video
        
        # Create mock FileStorage
        with open(temp_video_file, 'rb') as f:
            file_storage = FileStorage(
                stream=f,
                filename='duplicate_video.mp4',
                content_type='video/mp4'
            )
            
            # Upload video
            metadata = service.upload_video(file_storage)
        
        # Should return existing video metadata
        assert metadata.id == 456
        assert metadata.filename == 'existing_video.mp4'
        
        # Should not insert new video
        mock_queries.insert_video.assert_not_called()
    
    def test_upload_video_no_file(self, service):
        """Test upload fails when no file provided."""
        with pytest.raises(ValueError, match="No file provided"):
            service.upload_video(None)
    
    def test_upload_video_invalid_format(self, service):
        """Test upload fails for invalid video format."""
        # Create mock FileStorage with invalid extension
        mock_file = Mock(spec=FileStorage)
        mock_file.filename = 'video.mkv'
        
        with pytest.raises(ValueError, match="Invalid video format"):
            service.upload_video(mock_file)
    
    @patch('services.video_processor.queries')
    def test_upload_video_cleanup_on_error(self, mock_queries, service, temp_video_file):
        """Test file cleanup when upload fails."""
        # Mock database to raise error
        mock_queries.get_video_by_hash.return_value = None
        mock_queries.insert_video.side_effect = Exception("Database error")
        
        # Create mock FileStorage
        with open(temp_video_file, 'rb') as f:
            file_storage = FileStorage(
                stream=f,
                filename='test_video.mp4',
                content_type='video/mp4'
            )
            
            # Upload should fail
            with pytest.raises(Exception, match="Database error"):
                service.upload_video(file_storage)
        
        # Verify uploaded file was cleaned up
        # (We can't easily verify this without knowing the generated filename)
        # This is a limitation of the current test setup
    
    @patch('services.video_processor.queries')
    def test_get_detections_at_timestamp_success(self, mock_queries, service):
        """Test successful retrieval of detections at timestamp."""
        # Mock detection data
        mock_detections = [
            {
                'person_id': 1,
                'person_name': 'John Doe',
                'bbox': {'x1': 100, 'y1': 150, 'x2': 200, 'y2': 250},
                'recognition_confidence': 0.92,
                'detection_confidence': 0.98
            },
            {
                'person_id': None,
                'person_name': 'Unknown',
                'bbox': {'x1': 300, 'y1': 180, 'x2': 400, 'y2': 280},
                'recognition_confidence': 0.35,
                'detection_confidence': 0.95
            }
        ]
        mock_queries.get_detections_at_timestamp.return_value = mock_detections
        
        # Call method
        detections = service.get_detections_at_timestamp(
            video_id=123,
            timestamp=45.2,
            tolerance=0.25
        )
        
        # Verify results
        assert len(detections) == 2
        assert detections[0]['person_name'] == 'John Doe'
        assert detections[0]['recognition_confidence'] == 0.92
        assert detections[1]['person_name'] == 'Unknown'
        assert detections[1]['recognition_confidence'] == 0.35
        
        # Verify database call
        mock_queries.get_detections_at_timestamp.assert_called_once_with(
            service.db, 123, 45.2, 0.25
        )
    
    @patch('services.video_processor.queries')
    def test_get_detections_at_timestamp_default_tolerance(self, mock_queries, service):
        """Test default tolerance value of 0.25 seconds."""
        mock_queries.get_detections_at_timestamp.return_value = []
        
        # Call without tolerance parameter
        service.get_detections_at_timestamp(video_id=123, timestamp=10.0)
        
        # Verify default tolerance was used
        mock_queries.get_detections_at_timestamp.assert_called_once_with(
            service.db, 123, 10.0, 0.25
        )
    
    @patch('services.video_processor.queries')
    def test_get_detections_at_timestamp_custom_tolerance(self, mock_queries, service):
        """Test custom tolerance value."""
        mock_queries.get_detections_at_timestamp.return_value = []
        
        # Call with custom tolerance
        service.get_detections_at_timestamp(
            video_id=123,
            timestamp=10.0,
            tolerance=0.5
        )
        
        # Verify custom tolerance was used
        mock_queries.get_detections_at_timestamp.assert_called_once_with(
            service.db, 123, 10.0, 0.5
        )
    
    @patch('services.video_processor.queries')
    def test_get_detections_at_timestamp_empty_result(self, mock_queries, service):
        """Test handling of empty detection results."""
        mock_queries.get_detections_at_timestamp.return_value = []
        
        # Call method
        detections = service.get_detections_at_timestamp(
            video_id=123,
            timestamp=100.0
        )
        
        # Verify empty list returned
        assert detections == []
        assert isinstance(detections, list)
    
    @patch('services.video_processor.queries')
    def test_reprocess_video_success(self, mock_queries, service, temp_video_file):
        """Test successful video reprocessing."""
        # Mock video metadata
        mock_video = {
            'id': 123,
            'filename': 'test_video.mp4',
            'file_path': temp_video_file,
            'duration_seconds': 5.0,
            'fps': 1.0,
            'width': 640,
            'height': 480,
            'status': 'processed'
        }
        mock_queries.get_video_by_id.return_value = mock_video
        
        # Mock active model version
        mock_active_model = {
            'version_number': 2,
            'num_classes': 10,
            'cross_validation_accuracy': 0.95
        }
        mock_queries.get_active_model_version.return_value = mock_active_model
        
        # Mock database connection for deletion and update
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 5  # Simulate 5 rows deleted
        mock_db_conn.cursor.return_value = mock_cursor
        service.db.get_connection.return_value = mock_db_conn
        service.db.return_connection = Mock()
        
        # Mock process_video to avoid actual processing
        with patch.object(service, 'process_video') as mock_process:
            # Call reprocess_video
            result = service.reprocess_video(video_id=123, model_version=2)
        
        # Verify result
        assert result['video_id'] == 123
        assert result['status'] == 'completed'
        assert result['model_version'] == 2
        assert 'job_id' in result
        
        # Verify database operations
        mock_queries.get_video_by_id.assert_called_once_with(service.db, 123)
        mock_queries.insert_video_job.assert_called_once()
        mock_queries.update_video_record_status.assert_called()
        
        # Verify deletion queries
        delete_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        assert any('DELETE FROM timeline_entries' in call for call in delete_calls)
        assert any('DELETE FROM video_detections' in call for call in delete_calls)
        
        # Verify update query for reprocessed_at and model_version
        update_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        assert any('UPDATE videos SET reprocessed_at' in call for call in update_calls)
        
        # Verify process_video was called
        mock_process.assert_called_once()
    
    @patch('services.video_processor.queries')
    def test_reprocess_video_with_default_model_version(self, mock_queries, service, temp_video_file):
        """Test reprocessing uses active model version when not specified."""
        # Mock video metadata
        mock_video = {
            'id': 123,
            'filename': 'test_video.mp4',
            'file_path': temp_video_file,
            'status': 'processed'
        }
        mock_queries.get_video_by_id.return_value = mock_video
        
        # Mock active model version
        mock_active_model = {
            'version_number': 3,
            'num_classes': 15,
            'cross_validation_accuracy': 0.97
        }
        mock_queries.get_active_model_version.return_value = mock_active_model
        
        # Mock database connection
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 0
        mock_db_conn.cursor.return_value = mock_cursor
        service.db.get_connection.return_value = mock_db_conn
        service.db.return_connection = Mock()
        
        # Mock process_video
        with patch.object(service, 'process_video'):
            # Call without model_version parameter
            result = service.reprocess_video(video_id=123)
        
        # Verify active model version was used
        assert result['model_version'] == 3
        mock_queries.get_active_model_version.assert_called_once()
    
    @patch('services.video_processor.queries')
    def test_reprocess_video_nonexistent_video(self, mock_queries, service):
        """Test reprocessing fails for nonexistent video."""
        # Mock video not found
        mock_queries.get_video_by_id.return_value = None
        
        # Call should raise ValueError
        with pytest.raises(ValueError, match="Video with ID 999 does not exist"):
            service.reprocess_video(video_id=999)
    
    @patch('services.video_processor.queries')
    def test_reprocess_video_missing_file(self, mock_queries, service):
        """Test reprocessing fails when video file is missing."""
        # Mock video with nonexistent file path
        mock_video = {
            'id': 123,
            'filename': 'test_video.mp4',
            'file_path': '/nonexistent/path/video.mp4',
            'status': 'processed'
        }
        mock_queries.get_video_by_id.return_value = mock_video
        
        # Call should raise ValueError
        with pytest.raises(ValueError, match="Video file not found"):
            service.reprocess_video(video_id=123)
    
    @patch('services.video_processor.queries')
    def test_reprocess_video_deletion_failure(self, mock_queries, service, temp_video_file):
        """Test reprocessing handles deletion failures gracefully."""
        # Mock video metadata
        mock_video = {
            'id': 123,
            'filename': 'test_video.mp4',
            'file_path': temp_video_file,
            'status': 'processed'
        }
        mock_queries.get_video_by_id.return_value = mock_video
        
        # Mock database connection that fails on deletion
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Database deletion error")
        mock_db_conn.cursor.return_value = mock_cursor
        service.db.get_connection.return_value = mock_db_conn
        service.db.return_connection = Mock()
        
        # Call should raise exception
        with pytest.raises(Exception, match="Failed to delete existing data"):
            service.reprocess_video(video_id=123)
        
        # Verify rollback was called
        mock_db_conn.rollback.assert_called_once()
    
    @patch('services.video_processor.queries')
    def test_reprocess_video_processing_failure(self, mock_queries, service, temp_video_file):
        """Test reprocessing handles processing failures and updates status."""
        # Mock video metadata
        mock_video = {
            'id': 123,
            'filename': 'test_video.mp4',
            'file_path': temp_video_file,
            'status': 'processed'
        }
        mock_queries.get_video_by_id.return_value = mock_video
        
        # Mock database connection for deletion (succeeds)
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 5
        mock_db_conn.cursor.return_value = mock_cursor
        service.db.get_connection.return_value = mock_db_conn
        service.db.return_connection = Mock()
        
        # Mock process_video to fail
        with patch.object(service, 'process_video') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            # Call should raise exception
            with pytest.raises(Exception, match="Processing failed"):
                service.reprocess_video(video_id=123)
        
        # Verify video status was updated to failed
        mock_queries.update_video_record_status.assert_called_with(
            service.db, 123, 'failed'
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
