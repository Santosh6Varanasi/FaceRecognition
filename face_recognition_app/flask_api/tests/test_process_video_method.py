"""
Test for VideoProcessorService.process_video() method.
Verifies the frame extraction and face detection pipeline integration.
"""

import os
import sys
import pytest
import tempfile
import cv2
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the inference_service import to avoid dependency issues
sys.modules['services.inference_service'] = Mock()

from services.video_processor import VideoProcessorService


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    temp_path = temp_file.name
    temp_file.close()
    
    # Create a simple video with 3 frames at 1 FPS
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, 1.0, (640, 480))
    
    for i in range(3):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (i * 80, i * 80, i * 80)
        out.write(frame)
    
    out.release()
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.remove(temp_path)


@patch('services.video_processor.queries')
@patch('services.video_processor.inference_service')
def test_process_video_method_success(mock_inference_service, mock_queries, temp_video_file):
    """Test that process_video method extracts frames and calls face detection."""
    # Setup mocks
    mock_db = Mock()
    video_id = 123
    job_id = str(uuid.uuid4())
    
    # Mock database queries
    mock_queries.insert_video_session = Mock()
    mock_queries.update_video_job_status = Mock()
    mock_queries.update_video_record_status = Mock()
    mock_queries.get_video_session_face_counts = Mock(return_value={
        'unique_unknowns': 2,
        'unique_known': 1
    })
    
    # Mock inference service
    mock_inference_service.run_inference = Mock(return_value={
        'detections': [],
        'frame_id': 1,
        'processing_time_ms': 100
    })
    
    # Create service and process video
    service = VideoProcessorService(mock_db)
    service.process_video(video_id, job_id, temp_video_file)
    
    # Verify video session was created
    mock_queries.insert_video_session.assert_called_once()
    
    # Verify inference was called for each frame (3 frames at 1 FPS)
    assert mock_inference_service.run_inference.call_count == 3
    
    # Verify job status was updated
    assert mock_queries.update_video_job_status.call_count >= 2  # At least running and completed
    
    # Verify video record status was updated
    mock_queries.update_video_record_status.assert_called_once()
    update_call = mock_queries.update_video_record_status.call_args
    assert update_call[0][1] == video_id
    assert update_call[0][2] == 'processed'


@patch('services.video_processor.queries')
def test_process_video_method_invalid_file(mock_queries):
    """Test that process_video handles invalid video file gracefully."""
    mock_db = Mock()
    video_id = 123
    job_id = str(uuid.uuid4())
    invalid_path = '/nonexistent/video.mp4'
    
    # Mock database queries
    mock_queries.update_video_job_status = Mock()
    mock_queries.update_video_record_status = Mock()
    
    # Create service and process invalid video
    service = VideoProcessorService(mock_db)
    service.process_video(video_id, job_id, invalid_path)
    
    # Verify job status was updated to failed
    mock_queries.update_video_job_status.assert_called_once()
    call_args = mock_queries.update_video_job_status.call_args
    assert call_args[0][1] == job_id
    assert call_args[0][2] == 'failed'
    
    # Verify video record status was updated to failed
    mock_queries.update_video_record_status.assert_called_once()
    call_args = mock_queries.update_video_record_status.call_args
    assert call_args[0][1] == video_id
    assert call_args[0][2] == 'failed'


@patch('services.video_processor.queries')
@patch('services.video_processor.inference_service')
def test_process_video_method_frame_extraction_at_1fps(mock_inference_service, mock_queries, temp_video_file):
    """Test that frames are extracted at exactly 1 FPS."""
    mock_db = Mock()
    video_id = 123
    job_id = str(uuid.uuid4())
    
    # Mock database queries
    mock_queries.insert_video_session = Mock()
    mock_queries.update_video_job_status = Mock()
    mock_queries.update_video_record_status = Mock()
    mock_queries.get_video_session_face_counts = Mock(return_value={
        'unique_unknowns': 0,
        'unique_known': 0
    })
    
    # Track timestamps passed to inference
    timestamps = []
    def capture_timestamp(frame, session_id, db, timestamp_ms=0):
        timestamps.append(timestamp_ms)
        return {'detections': [], 'frame_id': 1, 'processing_time_ms': 100}
    
    mock_inference_service.run_inference = Mock(side_effect=capture_timestamp)
    
    # Create service and process video
    service = VideoProcessorService(mock_db)
    service.process_video(video_id, job_id, temp_video_file)
    
    # Verify timestamps are at 1 second intervals (1000ms)
    # Video is 3 seconds long at 1 FPS, so we expect timestamps: 0, 1000, 2000
    assert len(timestamps) == 3
    assert timestamps[0] == 0
    assert timestamps[1] == 1000
    assert timestamps[2] == 2000


@patch('services.video_processor.queries')
@patch('services.video_processor.inference_service')
def test_process_video_method_batch_progress_updates(mock_inference_service, mock_queries, temp_video_file):
    """Test that progress updates are sent during batch processing."""
    mock_db = Mock()
    video_id = 123
    job_id = str(uuid.uuid4())
    
    # Mock database queries
    mock_queries.insert_video_session = Mock()
    mock_queries.update_video_job_status = Mock()
    mock_queries.update_video_record_status = Mock()
    mock_queries.get_video_session_face_counts = Mock(return_value={
        'unique_unknowns': 0,
        'unique_known': 0
    })
    
    mock_inference_service.run_inference = Mock(return_value={
        'detections': [], 'frame_id': 1, 'processing_time_ms': 100
    })
    
    # Create service and process video
    service = VideoProcessorService(mock_db)
    service.process_video(video_id, job_id, temp_video_file)
    
    # Verify progress updates were sent
    # Should have: initial 'running', progress updates, and final 'completed'
    status_updates = mock_queries.update_video_job_status.call_args_list
    
    # Check that we have running and completed statuses
    statuses = [call[0][2] for call in status_updates]
    assert 'running' in statuses
    assert 'completed' in statuses


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
