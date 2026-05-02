"""
Unit tests for the FaceRecognitionApp class.

Tests component initialization, error handling, and shutdown behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.config import AppConfig
import sys
import os

# Add parent directory to path to import main module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import FaceRecognitionApp


class TestFaceRecognitionAppInitialization:
    """Test suite for FaceRecognitionApp initialization."""
    
    def test_init_creates_all_components(self):
        """Test that __init__ creates all three components."""
        config = AppConfig()
        
        with patch('main.DisplayRenderer') as mock_display, \
             patch('main.CameraHandler') as mock_camera, \
             patch('main.APIClient') as mock_api:
            
            # Mock camera initialization to return True
            mock_camera_instance = Mock()
            mock_camera_instance.initialize.return_value = True
            mock_camera.return_value = mock_camera_instance
            
            app = FaceRecognitionApp(config)
            
            # Verify all components were instantiated
            mock_display.assert_called_once_with(window_name=config.display_window_name)
            mock_camera.assert_called_once_with(
                camera_index=config.camera_index,
                width=config.camera_width,
                height=config.camera_height
            )
            mock_api.assert_called_once_with(
                base_url=config.api_base_url,
                timeout=config.api_timeout
            )
    
    def test_init_handles_camera_failure(self):
        """Test that camera initialization failure is handled gracefully."""
        config = AppConfig()
        
        with patch('main.DisplayRenderer'), \
             patch('main.CameraHandler') as mock_camera, \
             patch('main.APIClient'):
            
            # Mock camera initialization to return False
            mock_camera_instance = Mock()
            mock_camera_instance.initialize.return_value = False
            mock_camera.return_value = mock_camera_instance
            
            app = FaceRecognitionApp(config)
            
            # Camera should be None after failed initialization
            assert app.camera is None
    
    def test_init_handles_display_exception(self):
        """Test that display initialization exception is handled."""
        config = AppConfig()
        
        with patch('main.DisplayRenderer', side_effect=Exception("Display error")), \
             patch('main.CameraHandler') as mock_camera, \
             patch('main.APIClient'):
            
            mock_camera_instance = Mock()
            mock_camera_instance.initialize.return_value = True
            mock_camera.return_value = mock_camera_instance
            
            app = FaceRecognitionApp(config)
            
            # Display should be None after exception
            assert app.display is None
    
    def test_is_ready_returns_true_when_all_components_initialized(self):
        """Test that _is_ready returns True when all components are present."""
        config = AppConfig()
        
        with patch('main.DisplayRenderer'), \
             patch('main.CameraHandler') as mock_camera, \
             patch('main.APIClient'):
            
            mock_camera_instance = Mock()
            mock_camera_instance.initialize.return_value = True
            mock_camera.return_value = mock_camera_instance
            
            app = FaceRecognitionApp(config)
            
            # All components should be initialized
            assert app._is_ready() is True
    
    def test_is_ready_returns_false_when_camera_missing(self):
        """Test that _is_ready returns False when camera is not initialized."""
        config = AppConfig()
        
        with patch('main.DisplayRenderer'), \
             patch('main.CameraHandler') as mock_camera, \
             patch('main.APIClient'):
            
            mock_camera_instance = Mock()
            mock_camera_instance.initialize.return_value = False
            mock_camera.return_value = mock_camera_instance
            
            app = FaceRecognitionApp(config)
            
            # Camera failed to initialize
            assert app._is_ready() is False
    
    def test_shutdown_releases_camera(self):
        """Test that shutdown releases camera resources."""
        config = AppConfig()
        
        with patch('main.DisplayRenderer'), \
             patch('main.CameraHandler') as mock_camera, \
             patch('main.APIClient'), \
             patch('cv2.destroyAllWindows'):
            
            mock_camera_instance = Mock()
            mock_camera_instance.initialize.return_value = True
            mock_camera.return_value = mock_camera_instance
            
            app = FaceRecognitionApp(config)
            app.shutdown()
            
            # Verify camera.release() was called
            mock_camera_instance.release.assert_called_once()
    
    def test_shutdown_handles_missing_components(self):
        """Test that shutdown handles None components gracefully."""
        config = AppConfig()
        
        with patch('main.DisplayRenderer', side_effect=Exception("Display error")), \
             patch('main.CameraHandler', side_effect=Exception("Camera error")), \
             patch('main.APIClient', side_effect=Exception("API error")), \
             patch('cv2.destroyAllWindows'):
            
            app = FaceRecognitionApp(config)
            
            # All components should be None
            assert app.display is None
            assert app.camera is None
            assert app.api_client is None
            
            # Shutdown should not raise exceptions
            app.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
