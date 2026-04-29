"""
Unit tests for DisplayRenderer.draw_detections method.

Tests the bounding box drawing logic for known and unknown faces.
"""

import numpy as np
import pytest
from src.display_renderer import DisplayRenderer
from src.models import Detection, BoundingBox


def test_draw_detections_known_face():
    """Verify green bounding box is drawn for known faces."""
    # Create a test frame (100x100 black image)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Create a detection for a known face
    detection = Detection(
        bbox=BoundingBox(x1=10, y1=10, x2=50, y2=50),
        name="John Doe",
        confidence=0.87,
        detection_confidence=0.95
    )
    
    # Create renderer (without creating window for testing)
    renderer = DisplayRenderer()
    
    # Draw detections
    result_frame = renderer.draw_detections(frame, [detection])
    
    # Verify the frame was modified (not the same as input)
    assert result_frame is not frame
    
    # Verify green pixels exist at the bounding box edges
    # Top-left corner should have green pixels
    assert result_frame[10, 10, 1] == 255  # Green channel
    assert result_frame[10, 10, 0] == 0    # Blue channel
    assert result_frame[10, 10, 2] == 0    # Red channel


def test_draw_detections_unknown_face():
    """Verify red bounding box is drawn for unknown faces."""
    # Create a test frame (100x100 black image)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Create a detection for an unknown face
    detection = Detection(
        bbox=BoundingBox(x1=10, y1=10, x2=50, y2=50),
        name="Unknown",
        confidence=0.45,
        detection_confidence=0.92
    )
    
    # Create renderer
    renderer = DisplayRenderer()
    
    # Draw detections
    result_frame = renderer.draw_detections(frame, [detection])
    
    # Verify the frame was modified
    assert result_frame is not frame
    
    # Verify red pixels exist at the bounding box edges
    # Top-left corner should have red pixels
    assert result_frame[10, 10, 2] == 255  # Red channel
    assert result_frame[10, 10, 0] == 0    # Blue channel
    assert result_frame[10, 10, 1] == 0    # Green channel


def test_draw_detections_multiple_faces():
    """Verify multiple detections are rendered correctly."""
    # Create a test frame (200x200 black image)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    
    # Create multiple detections
    detections = [
        Detection(
            bbox=BoundingBox(x1=10, y1=10, x2=50, y2=50),
            name="Alice",
            confidence=0.90,
            detection_confidence=0.95
        ),
        Detection(
            bbox=BoundingBox(x1=100, y1=100, x2=150, y2=150),
            name="Unknown",
            confidence=0.40,
            detection_confidence=0.88
        )
    ]
    
    # Create renderer
    renderer = DisplayRenderer()
    
    # Draw detections
    result_frame = renderer.draw_detections(frame, detections)
    
    # Verify the frame was modified
    assert result_frame is not frame
    
    # Verify first detection has green box
    assert result_frame[10, 10, 1] == 255  # Green channel
    
    # Verify second detection has red box
    assert result_frame[100, 100, 2] == 255  # Red channel


def test_draw_detections_empty_list():
    """Verify no crash when detection list is empty."""
    # Create a test frame
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Create renderer
    renderer = DisplayRenderer()
    
    # Draw empty detections list
    result_frame = renderer.draw_detections(frame, [])
    
    # Verify frame is returned (should be a copy)
    assert result_frame is not None
    assert result_frame.shape == frame.shape


def test_draw_detections_none_frame():
    """Verify None frame is handled gracefully."""
    # Create renderer
    renderer = DisplayRenderer()
    
    # Draw detections on None frame
    result_frame = renderer.draw_detections(None, [])
    
    # Verify None is returned
    assert result_frame is None


def test_draw_detections_empty_frame():
    """Verify empty frame is handled gracefully."""
    # Create empty frame
    frame = np.array([])
    
    # Create renderer
    renderer = DisplayRenderer()
    
    # Draw detections on empty frame
    result_frame = renderer.draw_detections(frame, [])
    
    # Verify empty frame is returned
    assert result_frame.size == 0


def test_add_fps_overlay():
    """Verify FPS overlay is added to the frame."""
    # Create a test frame (100x100 black image)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Create renderer
    renderer = DisplayRenderer()
    
    # Add FPS overlay
    fps = 15.7
    result_frame = renderer.add_fps_overlay(frame, fps)
    
    # Verify the frame was modified (not the same as input)
    assert result_frame is not frame
    
    # Verify white pixels exist in the top-left corner (where FPS text is rendered)
    # Check for white text pixels (255, 255, 255)
    white_pixels_found = False
    for y in range(10, 30):  # Check area where text should be
        for x in range(10, 80):
            if (result_frame[y, x, 0] == 255 and 
                result_frame[y, x, 1] == 255 and 
                result_frame[y, x, 2] == 255):
                white_pixels_found = True
                break
        if white_pixels_found:
            break
    
    assert white_pixels_found, "FPS text (white pixels) should be present in top-left corner"
    
    # Verify black background pixels exist (0, 0, 0)
    black_pixels_found = False
    for y in range(10, 30):
        for x in range(10, 80):
            if (result_frame[y, x, 0] == 0 and 
                result_frame[y, x, 1] == 0 and 
                result_frame[y, x, 2] == 0):
                black_pixels_found = True
                break
        if black_pixels_found:
            break
    
    assert black_pixels_found, "Black background should be present for FPS overlay"


def test_add_fps_overlay_none_frame():
    """Verify None frame is handled gracefully in FPS overlay."""
    # Create renderer
    renderer = DisplayRenderer()
    
    # Add FPS overlay to None frame
    result_frame = renderer.add_fps_overlay(None, 10.0)
    
    # Verify None is returned
    assert result_frame is None


def test_add_fps_overlay_empty_frame():
    """Verify empty frame is handled gracefully in FPS overlay."""
    # Create empty frame
    frame = np.array([])
    
    # Create renderer
    renderer = DisplayRenderer()
    
    # Add FPS overlay to empty frame
    result_frame = renderer.add_fps_overlay(frame, 10.0)
    
    # Verify empty frame is returned
    assert result_frame.size == 0


def test_add_fps_overlay_various_fps_values():
    """Verify FPS overlay works with various FPS values."""
    # Create a test frame
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Create renderer
    renderer = DisplayRenderer()
    
    # Test with different FPS values
    fps_values = [0.0, 5.5, 15.7, 30.0, 60.0, 120.5]
    
    for fps in fps_values:
        result_frame = renderer.add_fps_overlay(frame, fps)
        
        # Verify frame was modified
        assert result_frame is not frame
        assert result_frame.shape == frame.shape
