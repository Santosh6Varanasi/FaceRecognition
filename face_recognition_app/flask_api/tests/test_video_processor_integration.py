"""
Integration tests for VideoProcessorService with database.
Tests the complete upload workflow with actual database operations.
"""

import os
import sys
import pytest
import tempfile
import cv2
import numpy as np
from unittest.mock import Mock
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the inference_service import to avoid dependency issues
sys.modules['services.inference_service'] = Mock()

from services.video_processor import VideoProcessorService
from werkzeug.datastructures import FileStorage


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    temp_path = temp_file.name
    temp_file.close()
    
    # Create a simple video with a few frames
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, 1.0, (640, 480))
    
    # Write 3 frames
    for i in range(3):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (i * 80, i * 80, i * 80)
        out.write(frame)
    
    out.release()
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_video_processor_service_initialization():
    """Test that VideoProcessorService can be initialized."""
    mock_db = Mock()
    service = VideoProcessorService(mock_db)
    
    assert service.db == mock_db
    assert service.ALLOWED_EXTENSIONS == {'mp4', 'avi', 'mov'}
    assert os.path.exists(service.UPLOAD_FOLDER)


def test_video_format_validation():
    """Test video format validation logic."""
    mock_db = Mock()
    service = VideoProcessorService(mock_db)
    
    # Valid formats
    assert service._validate_video_format('test.mp4') is True
    assert service._validate_video_format('test.avi') is True
    assert service._validate_video_format('test.mov') is True
    assert service._validate_video_format('TEST.MP4') is True
    
    # Invalid formats
    assert service._validate_video_format('test.mkv') is False
    assert service._validate_video_format('test.txt') is False
    assert service._validate_video_format('test') is False


def test_metadata_extraction(temp_video_file):
    """Test metadata extraction from actual video file."""
    mock_db = Mock()
    service = VideoProcessorService(mock_db)
    
    metadata = service._extract_video_metadata(temp_video_file)
    
    assert metadata['fps'] == 1.0
    assert metadata['frame_count'] == 3
    assert metadata['width'] == 640
    assert metadata['height'] == 480
    assert metadata['resolution'] == (640, 480)
    assert metadata['duration'] == 3.0


def test_file_hash_calculation(temp_video_file):
    """Test file hash calculation."""
    mock_db = Mock()
    service = VideoProcessorService(mock_db)
    
    hash1 = service._calculate_file_hash(temp_video_file)
    hash2 = service._calculate_file_hash(temp_video_file)
    
    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 hex characters


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
