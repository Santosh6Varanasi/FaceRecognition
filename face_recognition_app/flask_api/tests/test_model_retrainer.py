"""
Unit tests for ModelRetrainerService class.

Tests verify:
1. trigger_retrain() creates job and returns job_id
2. train_model() fetches embeddings, trains SVM, and stores model
3. get_retrain_status() retrieves job status by job_id
4. Model serialization and version management
5. Cross-validation with 5-fold strategy
6. Error handling and job status updates

Requirements: 10.2, 10.3, 10.4
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import io
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from services.model_retrainer import ModelRetrainerService


class TestModelRetrainerService:
    """Test suite for ModelRetrainerService class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.db_connection_mock = Mock()
        self.service = ModelRetrainerService(self.db_connection_mock)
    
    # -------------------------------------------------------------------------
    # Tests for trigger_retrain()
    # -------------------------------------------------------------------------
    
    @patch('services.model_retrainer.create_job')
    @patch('services.model_retrainer.update_job')
    @patch('services.model_retrainer.threading.Thread')
    def test_trigger_retrain_creates_job_and_returns_job_id(
        self, mock_thread, mock_update_job, mock_create_job
    ):
        """Test trigger_retrain creates a job and returns unique job_id."""
        # Setup
        expected_job_id = "test-job-uuid-12345"
        mock_create_job.return_value = expected_job_id
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Execute
        job_id = self.service.trigger_retrain()
        
        # Verify job creation
        mock_create_job.assert_called_once()
        
        # Verify job status updated to running
        mock_update_job.assert_called_once_with(expected_job_id, status="running")
        
        # Verify thread created and started
        mock_thread.assert_called_once()
        thread_call_args = mock_thread.call_args
        assert thread_call_args[1]['target'] == self.service._run_training_pipeline
        assert thread_call_args[1]['args'] == (expected_job_id,)
        assert thread_call_args[1]['daemon'] is True
        mock_thread_instance.start.assert_called_once()
        
        # Verify return value
        assert job_id == expected_job_id
    
    @patch('services.model_retrainer.create_job')
    @patch('services.model_retrainer.update_job')
    @patch('services.model_retrainer.threading.Thread')
    def test_trigger_retrain_launches_background_thread(
        self, mock_thread, mock_update_job, mock_create_job
    ):
        """Test trigger_retrain launches daemon thread for training."""
        # Setup
        mock_create_job.return_value = "job-123"
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Execute
        self.service.trigger_retrain()
        
        # Verify daemon thread started
        mock_thread_instance.start.assert_called_once()
    
    # -------------------------------------------------------------------------
    # Tests for get_retrain_status()
    # -------------------------------------------------------------------------
    
    @patch('services.model_retrainer.get_job')
    @patch('services.model_retrainer.job_to_dict')
    def test_get_retrain_status_returns_job_dict_when_found(
        self, mock_job_to_dict, mock_get_job
    ):
        """Test get_retrain_status returns job status dict when job exists."""
        # Setup
        job_id = "job-123"
        mock_job_state = Mock()
        mock_get_job.return_value = mock_job_state
        expected_dict = {
            "job_id": job_id,
            "status": "running",
            "progress_pct": 60,
            "message": "Training SVM classifier...",
            "version_number": None,
            "cv_accuracy": None,
            "num_classes": None,
        }
        mock_job_to_dict.return_value = expected_dict
        
        # Execute
        result = self.service.get_retrain_status(job_id)
        
        # Verify
        mock_get_job.assert_called_once_with(job_id)
        mock_job_to_dict.assert_called_once_with(mock_job_state)
        assert result == expected_dict
    
    @patch('services.model_retrainer.get_job')
    def test_get_retrain_status_returns_none_when_job_not_found(
        self, mock_get_job
    ):
        """Test get_retrain_status returns None when job_id doesn't exist."""
        # Setup
        mock_get_job.return_value = None
        
        # Execute
        result = self.service.get_retrain_status("nonexistent-job")
        
        # Verify
        assert result is None
    
    @patch('services.model_retrainer.get_job')
    @patch('services.model_retrainer.job_to_dict')
    def test_get_retrain_status_returns_completed_job_with_results(
        self, mock_job_to_dict, mock_get_job
    ):
        """Test get_retrain_status returns completed job with training results."""
        # Setup
        job_id = "job-completed"
        mock_job_state = Mock()
        mock_get_job.return_value = mock_job_state
        expected_dict = {
            "job_id": job_id,
            "status": "completed",
            "progress_pct": 100,
            "message": "Training complete",
            "version_number": 5,
            "cv_accuracy": 0.94,
            "num_classes": 25,
        }
        mock_job_to_dict.return_value = expected_dict
        
        # Execute
        result = self.service.get_retrain_status(job_id)
        
        # Verify completed job includes results
        assert result["status"] == "completed"
        assert result["version_number"] == 5
        assert result["cv_accuracy"] == 0.94
        assert result["num_classes"] == 25
    
    # -------------------------------------------------------------------------
    # Tests for train_model()
    # -------------------------------------------------------------------------
    
    @patch('services.model_retrainer.queries')
    @patch('services.model_retrainer.update_job')
    @patch('services.model_retrainer.normalize')
    @patch('services.model_retrainer.LabelEncoder')
    @patch('services.model_retrainer.SVC')
    @patch('services.model_retrainer.cross_val_score')
    @patch('services.model_retrainer.model_cache')
    def test_train_model_complete_workflow(
        self, mock_model_cache, mock_cv_score,
        mock_svc_class, mock_le_class, mock_normalize, mock_update_job, mock_queries
    ):
        """Test train_model executes complete training workflow."""
        # Setup
        job_id = "job-123"
        
        # Mock embeddings data
        embeddings_data = [
            (np.array([0.1, 0.2, 0.3]), "Alice"),
            (np.array([0.4, 0.5, 0.6]), "Alice"),
            (np.array([0.7, 0.8, 0.9]), "Bob"),
            (np.array([0.2, 0.3, 0.4]), "Bob"),
        ]
        mock_queries.get_embeddings_for_training.return_value = embeddings_data
        
        # Mock normalization
        X_norm = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9], [0.2, 0.3, 0.4]])
        mock_normalize.return_value = X_norm
        
        # Mock label encoder
        mock_le = Mock()
        mock_le.classes_ = np.array(["Alice", "Bob"])
        mock_le.fit_transform.return_value = np.array([0, 0, 1, 1])
        mock_le_class.return_value = mock_le
        
        # Mock SVM
        mock_svm = Mock()
        mock_svc_class.return_value = mock_svm
        
        # Mock cross-validation scores
        mock_cv_score.return_value = np.array([0.92, 0.94, 0.93, 0.95, 0.91])
        
        # Mock database operations
        mock_queries.get_next_version_number.return_value = 5
        mock_queries.save_model_version.return_value = 1
        
        # Execute - patch joblib.dump to avoid pickling mock objects
        with patch('joblib.dump'):
            result = self.service.train_model(job_id)
        
        # Verify embeddings loaded
        mock_queries.get_embeddings_for_training.assert_called_once_with(
            self.db_connection_mock,
            include_unknown_labeled=True
        )
        
        # Verify normalization
        mock_normalize.assert_called_once()
        
        # Verify label encoding
        mock_le.fit_transform.assert_called_once()
        
        # Verify SVM training
        mock_svc_class.assert_called_once_with(
            kernel="rbf", C=10, gamma="scale", probability=True
        )
        mock_cv_score.assert_called_once()
        mock_svm.fit.assert_called_once()
        
        # Verify model version saved
        mock_queries.save_model_version.assert_called_once()
        
        # Verify model cache refreshed
        mock_model_cache.refresh_model.assert_called_once()
        
        # Verify job status updates
        assert mock_update_job.call_count >= 4  # Multiple progress updates
        
        # Verify final status update
        final_update_call = [
            c for c in mock_update_job.call_args_list
            if c[1].get('status') == 'completed'
        ]
        assert len(final_update_call) == 1
        assert final_update_call[0][1]['progress_pct'] == 100
        assert final_update_call[0][1]['version_number'] == 5
        
        # Verify return value
        assert result["version_number"] == 5
        assert result["num_classes"] == 2
        assert result["num_training_samples"] == 4
        assert 0.0 <= result["cv_accuracy"] <= 1.0
    
    @patch('services.model_retrainer.queries')
    @patch('services.model_retrainer.update_job')
    def test_train_model_raises_error_with_insufficient_data(
        self, mock_update_job, mock_queries
    ):
        """Test train_model raises ValueError when less than 2 samples."""
        # Setup
        job_id = "job-123"
        embeddings_data = [
            (np.array([0.1, 0.2, 0.3]), "Alice"),
        ]
        mock_queries.get_embeddings_for_training.return_value = embeddings_data
        
        # Execute and verify exception
        with pytest.raises(ValueError) as exc_info:
            self.service.train_model(job_id)
        
        assert "Not enough training data" in str(exc_info.value)
        
        # Verify job status updated to failed
        failed_update_call = [
            c for c in mock_update_job.call_args_list
            if c[1].get('status') == 'failed'
        ]
        assert len(failed_update_call) == 1
    
    @patch('services.model_retrainer.queries')
    @patch('services.model_retrainer.update_job')
    @patch('services.model_retrainer.normalize')
    @patch('services.model_retrainer.LabelEncoder')
    @patch('services.model_retrainer.SVC')
    @patch('services.model_retrainer.cross_val_score')
    @patch('services.model_retrainer.model_cache')
    def test_train_model_uses_5_fold_cross_validation(
        self, mock_model_cache, mock_cv_score, mock_svc_class, mock_le_class,
        mock_normalize, mock_update_job, mock_queries
    ):
        """Test train_model uses 5-fold cross-validation for accuracy."""
        # Setup
        job_id = "job-123"
        
        # Create sufficient data for 5-fold CV
        embeddings_data = [
            (np.array([0.1, 0.2, 0.3]), "Alice"),
            (np.array([0.4, 0.5, 0.6]), "Alice"),
            (np.array([0.7, 0.8, 0.9]), "Bob"),
            (np.array([0.2, 0.3, 0.4]), "Bob"),
            (np.array([0.5, 0.6, 0.7]), "Charlie"),
            (np.array([0.8, 0.9, 1.0]), "Charlie"),
        ]
        mock_queries.get_embeddings_for_training.return_value = embeddings_data
        
        X_norm = np.array([[0.1, 0.2, 0.3]] * 6)
        mock_normalize.return_value = X_norm
        
        mock_le = Mock()
        mock_le.classes_ = np.array(["Alice", "Bob", "Charlie"])
        mock_le.fit_transform.return_value = np.array([0, 0, 1, 1, 2, 2])
        mock_le_class.return_value = mock_le
        
        mock_svm = Mock()
        mock_svc_class.return_value = mock_svm
        
        mock_cv_score.return_value = np.array([0.92, 0.94, 0.93, 0.95, 0.91])
        
        mock_queries.get_next_version_number.return_value = 1
        mock_queries.save_model_version.return_value = 1
        
        # Execute - patch joblib.dump to avoid pickling mock objects
        with patch('joblib.dump'):
            result = self.service.train_model(job_id)
        
        # Verify cross-validation called with correct parameters
        mock_cv_score.assert_called_once()
        cv_call_args = mock_cv_score.call_args
        # Check that cv parameter has n_splits=5 (or min(5, n_classes))
        cv_param = cv_call_args[1]['cv']
        assert hasattr(cv_param, 'n_splits')
        assert cv_param.n_splits <= 5
    
    @patch('services.model_retrainer.queries')
    @patch('services.model_retrainer.update_job')
    @patch('services.model_retrainer.normalize')
    @patch('services.model_retrainer.LabelEncoder')
    @patch('services.model_retrainer.SVC')
    @patch('services.model_retrainer.cross_val_score')
    @patch('services.model_retrainer.model_cache')
    def test_train_model_stores_model_metadata(
        self, mock_model_cache, mock_cv_score, mock_svc_class,
        mock_le_class, mock_normalize, mock_update_job, mock_queries
    ):
        """Test train_model stores model metadata in database."""
        # Setup
        job_id = "job-123"
        
        embeddings_data = [
            (np.array([0.1, 0.2, 0.3]), "Alice"),
            (np.array([0.4, 0.5, 0.6]), "Alice"),
            (np.array([0.7, 0.8, 0.9]), "Bob"),
            (np.array([0.2, 0.3, 0.4]), "Bob"),
        ]
        mock_queries.get_embeddings_for_training.return_value = embeddings_data
        
        X_norm = np.array([[0.1, 0.2, 0.3]] * 4)
        mock_normalize.return_value = X_norm
        
        mock_le = Mock()
        mock_le.classes_ = np.array(["Alice", "Bob"])
        mock_le.fit_transform.return_value = np.array([0, 0, 1, 1])
        mock_le_class.return_value = mock_le
        
        mock_svm = Mock()
        mock_svc_class.return_value = mock_svm
        
        mock_cv_score.return_value = np.array([0.92, 0.94, 0.93, 0.95, 0.91])
        
        mock_queries.get_next_version_number.return_value = 5
        mock_queries.save_model_version.return_value = 1
        
        # Execute - patch joblib.dump to avoid pickling mock objects
        with patch('joblib.dump'):
            result = self.service.train_model(job_id)
        
        # Verify save_model_version called with correct parameters
        mock_queries.save_model_version.assert_called_once()
        save_call_args = mock_queries.save_model_version.call_args[0]
        
        assert save_call_args[0] == self.db_connection_mock  # db connection
        assert save_call_args[1] == 5  # version_number
        assert isinstance(save_call_args[2], bytes)  # model_bytes
        assert isinstance(save_call_args[3], bytes)  # label_encoder_bytes
        assert save_call_args[4] == 2  # num_classes
        assert save_call_args[5] == 4  # num_training_samples
        assert 0.0 <= save_call_args[6] <= 1.0  # cv_accuracy
        assert isinstance(save_call_args[7], float)  # cv_std
        assert save_call_args[8] == {"kernel": "rbf", "C": 10, "gamma": "scale"}  # hyperparams
    
    @patch('services.model_retrainer.queries')
    @patch('services.model_retrainer.update_job')
    def test_train_model_updates_job_status_on_error(
        self, mock_update_job, mock_queries
    ):
        """Test train_model updates job status to failed on error."""
        # Setup
        job_id = "job-123"
        mock_queries.get_embeddings_for_training.side_effect = Exception("Database error")
        
        # Execute and verify exception
        with pytest.raises(Exception):
            self.service.train_model(job_id)
        
        # Verify job status updated to failed
        failed_update_call = [
            c for c in mock_update_job.call_args_list
            if c[1].get('status') == 'failed'
        ]
        assert len(failed_update_call) == 1
        assert "Database error" in failed_update_call[0][1]['message']
    
    # -------------------------------------------------------------------------
    # Tests for _run_training_pipeline()
    # -------------------------------------------------------------------------
    
    @patch.object(ModelRetrainerService, 'train_model')
    def test_run_training_pipeline_calls_train_model(self, mock_train_model):
        """Test _run_training_pipeline calls train_model with job_id."""
        # Setup
        job_id = "job-123"
        mock_train_model.return_value = {"version_number": 5}
        
        # Execute
        self.service._run_training_pipeline(job_id)
        
        # Verify
        mock_train_model.assert_called_once_with(job_id)
    
    @patch.object(ModelRetrainerService, 'train_model')
    def test_run_training_pipeline_handles_exceptions_gracefully(
        self, mock_train_model
    ):
        """Test _run_training_pipeline handles exceptions without crashing."""
        # Setup
        job_id = "job-123"
        mock_train_model.side_effect = Exception("Training failed")
        
        # Execute - should not raise exception
        self.service._run_training_pipeline(job_id)
        
        # Verify train_model was called
        mock_train_model.assert_called_once_with(job_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
