"""
Integration tests for Tasks 6 and 7 API endpoints.

Tests cover:
- Task 6: Video Operations API Endpoints
  - POST /api/videos/upload
  - POST /api/videos/{video_id}/process
  - GET /api/videos/{video_id}
  - GET /api/videos/{video_id}/detections
  - GET /api/videos/{video_id}/timeline
  - POST /api/videos/{video_id}/reprocess
  - POST /api/videos/reprocess-batch

- Task 7: Bulk Operations and Model Management API Endpoints
  - POST /api/unknown-faces/bulk-delete
  - POST /api/unknown-faces/bulk-reject
  - GET /api/unknown-faces/count
  - POST /api/model/retrain
  - GET /api/model/retrain/status/{job_id}
"""

import os
import sys
import pytest
import tempfile
import cv2
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock dependencies
sys.modules['services.inference_service'] = Mock()

from app import create_app
from db import queries


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    temp_path = temp_file.name
    temp_file.close()
    
    # Create a simple video with a few frames
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, 1.0, (640, 480))
    
    # Write 5 frames
    for i in range(5):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (i * 50, i * 50, i * 50)
        out.write(frame)
    
    out.release()
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def mock_db():
    """Create mock database connection."""
    mock = Mock()
    mock.get_connection = Mock(return_value=Mock())
    mock.return_connection = Mock()
    return mock


# ============================================================================
# Task 6: Video Operations API Endpoints Tests
# ============================================================================

class TestVideoUploadEndpoint:
    """Tests for POST /api/videos/upload (Task 6.1)"""
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_hash')
    @patch('routes.video.queries.insert_video')
    @patch('routes.video.queries.insert_video_job')
    @patch('routes.video.threading.Thread')
    def test_upload_video_success(self, mock_thread, mock_insert_job, 
                                   mock_insert_video, mock_get_by_hash, 
                                   mock_get_db, client, temp_video_file):
        """Test successful video upload returns 202 Accepted."""
        mock_get_db.return_value = Mock()
        mock_get_by_hash.return_value = None
        mock_insert_video.return_value = 123
        
        with open(temp_video_file, 'rb') as f:
            data = {
                'file': (f, 'test_video.mp4')
            }
            response = client.post('/api/videos/upload', 
                                   data=data,
                                   content_type='multipart/form-data')
        
        assert response.status_code == 202
        json_data = response.get_json()
        assert 'video_id' in json_data
        assert 'job_id' in json_data
        assert json_data['video_id'] == 123
    
    def test_upload_video_no_file(self, client):
        """Test upload without file returns 400 Bad Request."""
        response = client.post('/api/videos/upload', 
                               data={},
                               content_type='multipart/form-data')
        
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'error' in json_data
    
    def test_upload_video_invalid_format(self, client):
        """Test upload with invalid format returns 400 Bad Request."""
        data = {
            'file': (BytesIO(b'fake content'), 'test.txt')
        }
        response = client.post('/api/videos/upload', 
                               data=data,
                               content_type='multipart/form-data')
        
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Unsupported file format' in json_data['error']


class TestVideoMetadataEndpoint:
    """Tests for GET /api/videos/{video_id} (Task 6.3)"""
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    def test_get_video_metadata_success(self, mock_get_by_id, mock_get_db, client):
        """Test retrieving video metadata returns 200 OK."""
        from datetime import datetime
        
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = {
            'id': 123,
            'filename': 'test.mp4',
            'duration_seconds': 120.5,
            'frame_count': 120,
            'fps': 1.0,
            'width': 1920,
            'height': 1080,
            'uploaded_at': datetime(2024, 1, 15, 10, 30, 0),
            'last_processed_at': datetime(2024, 1, 15, 10, 35, 0),
            'reprocessed_at': None,
            'model_version': 3,
            'status': 'completed'
        }
        
        response = client.get('/api/videos/123')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['id'] == 123
        assert json_data['filename'] == 'test.mp4'
        assert json_data['duration'] == 120.5
        assert json_data['resolution'] == [1920, 1080]
        assert json_data['status'] == 'completed'
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    def test_get_video_metadata_not_found(self, mock_get_by_id, mock_get_db, client):
        """Test retrieving non-existent video returns 404 Not Found."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = None
        
        response = client.get('/api/videos/999')
        
        assert response.status_code == 404
        json_data = response.get_json()
        assert 'error' in json_data


class TestVideoProcessEndpoint:
    """Tests for POST /api/videos/{video_id}/process (Task 6.2)"""
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    @patch('routes.video.queries.insert_video_job')
    @patch('routes.video.threading.Thread')
    def test_process_video_success(self, mock_thread, mock_insert_job, 
                                    mock_get_by_id, mock_get_db, client):
        """Test triggering video processing returns 202 Accepted."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = {
            'id': 123,
            'status': 'pending',
            'file_path': '/path/to/video.mp4'
        }
        
        response = client.post('/api/videos/123/process')
        
        assert response.status_code == 202
        json_data = response.get_json()
        assert json_data['video_id'] == 123
        assert json_data['status'] == 'processing'
        assert 'job_id' in json_data
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    def test_process_video_not_found(self, mock_get_by_id, mock_get_db, client):
        """Test processing non-existent video returns 404 Not Found."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = None
        
        response = client.post('/api/videos/999/process')
        
        assert response.status_code == 404
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    def test_process_video_already_processing(self, mock_get_by_id, mock_get_db, client):
        """Test processing already-processing video returns 400 Bad Request."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = {
            'id': 123,
            'status': 'processing',
            'file_path': '/path/to/video.mp4'
        }
        
        response = client.post('/api/videos/123/process')
        
        assert response.status_code == 400


class TestVideoDetectionsEndpoint:
    """Tests for GET /api/videos/{video_id}/detections (Task 6.4)"""
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    @patch('routes.video.queries.get_detections_at_timestamp')
    def test_get_detections_success(self, mock_get_detections, mock_get_by_id, 
                                     mock_get_db, client):
        """Test retrieving detections at timestamp returns 200 OK."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = {'id': 123}
        mock_get_detections.return_value = [
            {
                'bbox_x1': 100, 'bbox_y1': 150, 'bbox_x2': 200, 'bbox_y2': 250,
                'person_name': 'John Doe',
                'recognition_confidence': 0.92,
                'detection_confidence': 0.98
            },
            {
                'bbox_x1': 300, 'bbox_y1': 180, 'bbox_x2': 400, 'bbox_y2': 280,
                'person_name': 'Unknown',
                'recognition_confidence': 0.35,
                'detection_confidence': 0.95
            }
        ]
        
        response = client.get('/api/videos/123/detections?timestamp=45.2&tolerance=0.25')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['video_id'] == 123
        assert json_data['timestamp'] == 45.2
        assert len(json_data['detections']) == 2
        assert json_data['detections'][0]['name'] == 'John Doe'
        assert json_data['detections'][0]['confidence'] == 0.92
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    def test_get_detections_missing_timestamp(self, mock_get_by_id, mock_get_db, client):
        """Test retrieving detections without timestamp returns 400 Bad Request."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = {'id': 123}
        
        response = client.get('/api/videos/123/detections')
        
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'error' in json_data


class TestVideoTimelineEndpoint:
    """Tests for GET /api/videos/{video_id}/timeline (Task 6.5)"""
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    @patch('routes.video.queries.get_timeline_entries')
    def test_get_timeline_success(self, mock_get_timeline, mock_get_by_id, 
                                   mock_get_db, client):
        """Test retrieving timeline entries returns 200 OK."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = {'id': 123}
        mock_get_timeline.return_value = [
            {
                'id': 1,
                'person_name': 'John Doe',
                'start_time': 10.5,
                'end_time': 45.2,
                'detection_count': 35,
                'avg_confidence': 0.89
            },
            {
                'id': 2,
                'person_name': 'Unknown',
                'start_time': 50.0,
                'end_time': 65.5,
                'detection_count': 16,
                'avg_confidence': 0.42
            }
        ]
        
        response = client.get('/api/videos/123/timeline')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['video_id'] == 123
        assert len(json_data['entries']) == 2
        assert json_data['entries'][0]['person_name'] == 'John Doe'
        assert json_data['entries'][0]['start_time'] == 10.5


class TestVideoReprocessEndpoint:
    """Tests for POST /api/videos/{video_id}/reprocess (Task 6.6)"""
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.queries.get_video_by_id')
    @patch('routes.video.threading.Thread')
    def test_reprocess_video_success(self, mock_thread, mock_get_by_id, 
                                      mock_get_db, client):
        """Test triggering video reprocessing returns 202 Accepted."""
        mock_get_db.return_value = Mock()
        mock_get_by_id.return_value = {
            'id': 123,
            'file_path': '/path/to/video.mp4'
        }
        
        response = client.post('/api/videos/123/reprocess',
                               json={'model_version': 4})
        
        assert response.status_code == 202
        json_data = response.get_json()
        assert json_data['video_id'] == 123
        assert json_data['status'] == 'reprocessing'


class TestVideoBatchReprocessEndpoint:
    """Tests for POST /api/videos/reprocess-batch (Task 6.7)"""
    
    @patch('routes.video.queries.get_db_connection')
    @patch('routes.video.threading.Thread')
    def test_batch_reprocess_success(self, mock_thread, mock_get_db, client):
        """Test batch reprocessing returns 202 Accepted."""
        mock_get_db.return_value = Mock()
        
        response = client.post('/api/videos/reprocess-batch',
                               json={'video_ids': [123, 124, 125], 'model_version': 4})
        
        assert response.status_code == 202
        json_data = response.get_json()
        assert 'job_id' in json_data
        assert json_data['video_count'] == 3
        assert json_data['status'] == 'queued'
    
    def test_batch_reprocess_invalid_body(self, client):
        """Test batch reprocessing with invalid body returns 400 Bad Request."""
        response = client.post('/api/videos/reprocess-batch',
                               json={'video_ids': []})
        
        assert response.status_code == 400


# ============================================================================
# Task 7: Bulk Operations and Model Management API Endpoints Tests
# ============================================================================

class TestBulkDeleteEndpoint:
    """Tests for POST /api/unknown-faces/bulk-delete (Task 7.1)"""
    
    @patch('routes.unknown_faces.queries.get_db_connection')
    @patch('routes.unknown_faces.BulkOperationHandler')
    def test_bulk_delete_success(self, mock_handler_class, mock_get_db, client):
        """Test bulk delete returns 200 OK with operation results."""
        mock_get_db.return_value = Mock()
        mock_handler = Mock()
        mock_handler.bulk_delete.return_value = {
            'success_count': 150,
            'failure_count': 0,
            'total_count': 150,
            'message': 'Successfully deleted 150 unknown face(s)'
        }
        mock_handler_class.return_value = mock_handler
        
        response = client.post('/api/unknown-faces/bulk-delete',
                               json={'filter_status': 'pending'})
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['operation_type'] == 'delete'
        assert json_data['affected_count'] == 150
        assert json_data['success_count'] == 150


class TestBulkRejectEndpoint:
    """Tests for POST /api/unknown-faces/bulk-reject (Task 7.2)"""
    
    @patch('routes.unknown_faces.queries.get_db_connection')
    @patch('routes.unknown_faces.BulkOperationHandler')
    def test_bulk_reject_success(self, mock_handler_class, mock_get_db, client):
        """Test bulk reject returns 200 OK with operation results."""
        mock_get_db.return_value = Mock()
        mock_handler = Mock()
        mock_handler.bulk_reject.return_value = {
            'success_count': 150,
            'failure_count': 0,
            'total_count': 150,
            'message': 'Successfully rejected 150 unknown face(s)'
        }
        mock_handler_class.return_value = mock_handler
        
        response = client.post('/api/unknown-faces/bulk-reject',
                               json={'filter_status': 'pending'})
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['operation_type'] == 'reject'
        assert json_data['affected_count'] == 150


class TestUnknownFacesCountEndpoint:
    """Tests for GET /api/unknown-faces/count (Task 7.3)"""
    
    @patch('routes.unknown_faces.queries.get_db_connection')
    @patch('routes.unknown_faces.BulkOperationHandler')
    def test_get_count_success(self, mock_handler_class, mock_get_db, client):
        """Test getting count returns 200 OK with count."""
        mock_get_db.return_value = Mock()
        mock_handler = Mock()
        mock_handler.get_affected_count.return_value = 150
        mock_handler_class.return_value = mock_handler
        
        response = client.get('/api/unknown-faces/count?filter_status=pending')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['filter_status'] == 'pending'
        assert json_data['count'] == 150


class TestModelRetrainEndpoint:
    """Tests for POST /api/model/retrain (Task 7.4)"""
    
    @patch('routes.model.queries.get_db_connection')
    @patch('routes.model.retraining_service.start_retraining_job')
    def test_trigger_retrain_success(self, mock_start_job, mock_get_db, client):
        """Test triggering retrain returns 202 Accepted with job_id."""
        mock_get_db.return_value = Mock()
        mock_start_job.return_value = 'retrain-job-xyz789'
        
        response = client.post('/api/model/retrain')
        
        assert response.status_code == 202
        json_data = response.get_json()
        assert json_data['job_id'] == 'retrain-job-xyz789'


class TestModelRetrainStatusEndpoint:
    """Tests for GET /api/model/retrain/status/{job_id} (Task 7.5)"""
    
    @patch('routes.model.get_job')
    @patch('routes.model.job_to_dict')
    def test_get_retrain_status_success(self, mock_job_to_dict, mock_get_job, client):
        """Test getting retrain status returns 200 OK with status."""
        mock_job = Mock()
        mock_get_job.return_value = mock_job
        mock_job_to_dict.return_value = {
            'job_id': 'retrain-job-xyz789',
            'status': 'running',
            'progress_pct': 65.0,
            'message': 'Training SVM classifier (fold 4/5)'
        }
        
        response = client.get('/api/model/retrain/status/retrain-job-xyz789')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['job_id'] == 'retrain-job-xyz789'
        assert json_data['status'] == 'running'
        assert json_data['progress_pct'] == 65.0
    
    @patch('routes.model.get_job')
    def test_get_retrain_status_not_found(self, mock_get_job, client):
        """Test getting status for non-existent job returns 404 Not Found."""
        mock_get_job.return_value = None
        
        response = client.get('/api/model/retrain/status/invalid-job-id')
        
        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
