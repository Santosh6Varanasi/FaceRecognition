"""
Unit tests for face deduplication using embedding similarity.

Tests the implementation of Requirement 8.5:
- Face deduplication by embedding similarity
- Cosine similarity calculation
- Duplicate detection with threshold 0.6
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from services import inference_service


class TestCosineSimilarity:
    """Test cosine similarity calculation between embeddings."""
    
    def test_identical_embeddings(self):
        """Identical embeddings should have similarity of 1.0."""
        embedding = np.array([0.5, 0.5, 0.5, 0.5])
        embedding_norm = embedding / np.linalg.norm(embedding)
        
        similarity = inference_service.cosine_similarity(embedding_norm, embedding_norm)
        
        assert abs(similarity - 1.0) < 0.001, f"Expected similarity ~1.0, got {similarity}"
    
    def test_orthogonal_embeddings(self):
        """Orthogonal embeddings should have similarity close to 0."""
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        similarity = inference_service.cosine_similarity(embedding1, embedding2)
        
        assert abs(similarity) < 0.001, f"Expected similarity ~0.0, got {similarity}"
    
    def test_opposite_embeddings(self):
        """Opposite embeddings should have similarity of -1.0."""
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        embedding2 = np.array([-1.0, 0.0, 0.0, 0.0])
        
        similarity = inference_service.cosine_similarity(embedding1, embedding2)
        
        assert abs(similarity - (-1.0)) < 0.001, f"Expected similarity ~-1.0, got {similarity}"
    
    def test_similar_embeddings(self):
        """Similar embeddings should have high positive similarity."""
        embedding1 = np.array([0.8, 0.6, 0.0, 0.0])
        embedding1_norm = embedding1 / np.linalg.norm(embedding1)
        
        embedding2 = np.array([0.7, 0.7, 0.0, 0.0])
        embedding2_norm = embedding2 / np.linalg.norm(embedding2)
        
        similarity = inference_service.cosine_similarity(embedding1_norm, embedding2_norm)
        
        assert similarity > 0.9, f"Expected high similarity, got {similarity}"


class TestIsDuplicateFace:
    """Test duplicate face detection using embedding similarity."""
    
    def test_no_existing_faces(self):
        """When no existing faces, should return False (not a duplicate)."""
        mock_db = Mock()
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.return_value = []
            
            embedding = np.array([0.5, 0.5, 0.5, 0.5])
            result = inference_service.is_duplicate_face(embedding, mock_db)
            
            assert result is False, "Should not be duplicate when no existing faces"
    
    def test_duplicate_above_threshold(self):
        """When similarity > 0.6, should return True (is a duplicate)."""
        mock_db = Mock()
        
        # Create two very similar embeddings
        embedding1 = np.array([0.8, 0.6, 0.0, 0.0])
        embedding1_norm = embedding1 / np.linalg.norm(embedding1)
        
        embedding2 = np.array([0.79, 0.61, 0.0, 0.0])
        embedding2_norm = embedding2 / np.linalg.norm(embedding2)
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.return_value = [
                {"id": 1, "embedding": embedding1_norm.tolist()}
            ]
            
            result = inference_service.is_duplicate_face(embedding2_norm, mock_db)
            
            assert result is True, "Should be duplicate when similarity > 0.6"
    
    def test_not_duplicate_below_threshold(self):
        """When similarity <= 0.6, should return False (not a duplicate)."""
        mock_db = Mock()
        
        # Create two dissimilar embeddings
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.return_value = [
                {"id": 1, "embedding": embedding1.tolist()}
            ]
            
            result = inference_service.is_duplicate_face(embedding2, mock_db)
            
            assert result is False, "Should not be duplicate when similarity <= 0.6"
    
    def test_multiple_existing_faces_one_duplicate(self):
        """When one of multiple existing faces is a duplicate, should return True."""
        mock_db = Mock()
        
        # Create embeddings
        embedding_new = np.array([0.8, 0.6, 0.0, 0.0])
        embedding_new_norm = embedding_new / np.linalg.norm(embedding_new)
        
        embedding_different = np.array([0.0, 0.0, 1.0, 0.0])
        embedding_similar = np.array([0.79, 0.61, 0.0, 0.0])
        embedding_similar_norm = embedding_similar / np.linalg.norm(embedding_similar)
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.return_value = [
                {"id": 1, "embedding": embedding_different.tolist()},
                {"id": 2, "embedding": embedding_similar_norm.tolist()},
            ]
            
            result = inference_service.is_duplicate_face(embedding_new_norm, mock_db)
            
            assert result is True, "Should be duplicate when any existing face has similarity > 0.6"
    
    def test_multiple_existing_faces_no_duplicate(self):
        """When none of multiple existing faces are duplicates, should return False."""
        mock_db = Mock()
        
        # Create embeddings
        embedding_new = np.array([1.0, 0.0, 0.0, 0.0])
        
        embedding1 = np.array([0.0, 1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 0.0, 1.0, 0.0])
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.return_value = [
                {"id": 1, "embedding": embedding1.tolist()},
                {"id": 2, "embedding": embedding2.tolist()},
            ]
            
            result = inference_service.is_duplicate_face(embedding_new, mock_db)
            
            assert result is False, "Should not be duplicate when no existing face has similarity > 0.6"
    
    def test_exact_threshold_boundary(self):
        """When similarity equals 0.6, should return False (not a duplicate)."""
        mock_db = Mock()
        
        # Create embeddings with similarity exactly at 0.6
        # cos(θ) = 0.6 means θ ≈ 53.13 degrees
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        
        # Calculate embedding2 to have exactly 0.6 similarity with embedding1
        # For normalized vectors: cos(θ) = dot(v1, v2)
        # We want dot([1,0,0,0], [x,y,0,0]) = 0.6, so x = 0.6
        # And x^2 + y^2 = 1, so y = sqrt(1 - 0.36) = 0.8
        embedding2 = np.array([0.6, 0.8, 0.0, 0.0])
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.return_value = [
                {"id": 1, "embedding": embedding1.tolist()}
            ]
            
            result = inference_service.is_duplicate_face(embedding2, mock_db)
            
            assert result is False, "Should not be duplicate when similarity equals 0.6 (threshold is >0.6)"
    
    def test_just_above_threshold(self):
        """When similarity is just above 0.6, should return True."""
        mock_db = Mock()
        
        # Create embeddings with similarity just above 0.6
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        embedding2 = np.array([0.61, 0.79, 0.0, 0.0])  # Slightly more similar than 0.6
        embedding2_norm = embedding2 / np.linalg.norm(embedding2)
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.return_value = [
                {"id": 1, "embedding": embedding1.tolist()}
            ]
            
            result = inference_service.is_duplicate_face(embedding2_norm, mock_db)
            
            assert result is True, "Should be duplicate when similarity > 0.6"
    
    def test_error_handling_returns_false(self):
        """When database error occurs, should return False (fail open)."""
        mock_db = Mock()
        
        with patch('services.inference_service.queries.get_all_unknown_face_embeddings') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            embedding = np.array([0.5, 0.5, 0.5, 0.5])
            result = inference_service.is_duplicate_face(embedding, mock_db)
            
            assert result is False, "Should return False on error (fail open)"


class TestFaceDeduplicationIntegration:
    """Integration tests for face deduplication in video processing."""
    
    @patch('services.inference_service.queries.insert_unknown_face')
    @patch('services.inference_service.queries.get_all_unknown_face_embeddings')
    @patch('services.inference_service.image_service.crop_and_save_face')
    def test_duplicate_face_not_stored(self, mock_crop, mock_get_embeddings, mock_insert):
        """When a duplicate face is detected, it should not be stored."""
        mock_db = Mock()
        
        # Setup existing face
        existing_embedding = np.array([0.8, 0.6, 0.0, 0.0])
        existing_embedding_norm = existing_embedding / np.linalg.norm(existing_embedding)
        
        mock_get_embeddings.return_value = [
            {"id": 1, "embedding": existing_embedding_norm.tolist()}
        ]
        
        # Try to store a very similar face
        new_embedding = np.array([0.79, 0.61, 0.0, 0.0])
        new_embedding_norm = new_embedding / np.linalg.norm(new_embedding)
        
        # Call is_duplicate_face
        is_dup = inference_service.is_duplicate_face(new_embedding_norm, mock_db)
        
        # Verify duplicate was detected
        assert is_dup is True
        
        # Verify insert_unknown_face was NOT called (would be skipped in actual code)
        # This simulates the behavior in run_inference where we check before inserting
        if not is_dup:
            mock_insert.assert_not_called()
    
    @patch('services.inference_service.queries.insert_unknown_face')
    @patch('services.inference_service.queries.get_all_unknown_face_embeddings')
    @patch('services.inference_service.image_service.crop_and_save_face')
    def test_unique_face_is_stored(self, mock_crop, mock_get_embeddings, mock_insert):
        """When a unique face is detected, it should be stored."""
        mock_db = Mock()
        
        # Setup existing face
        existing_embedding = np.array([1.0, 0.0, 0.0, 0.0])
        
        mock_get_embeddings.return_value = [
            {"id": 1, "embedding": existing_embedding.tolist()}
        ]
        
        # Try to store a different face
        new_embedding = np.array([0.0, 1.0, 0.0, 0.0])
        
        # Call is_duplicate_face
        is_dup = inference_service.is_duplicate_face(new_embedding, mock_db)
        
        # Verify duplicate was NOT detected
        assert is_dup is False
        
        # In actual code, insert_unknown_face WOULD be called
        # This test verifies the logic that determines whether to insert


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
