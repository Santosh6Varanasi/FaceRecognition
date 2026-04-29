"""
Data models for the Python real-time face recognition application.

This module defines the core data structures used throughout the application:
- BoundingBox: Represents face detection bounding box coordinates
- Detection: Represents a single face detection with recognition results
- VideoSession: Represents a video streaming session
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BoundingBox:
    """
    Represents a rectangular bounding box around a detected face.
    
    Attributes:
        x1: Left edge x-coordinate (pixels)
        y1: Top edge y-coordinate (pixels)
        x2: Right edge x-coordinate (pixels)
        y2: Bottom edge y-coordinate (pixels)
    """
    x1: int
    y1: int
    x2: int
    y2: int
    
    def width(self) -> int:
        """Calculate the width of the bounding box."""
        return self.x2 - self.x1
    
    def height(self) -> int:
        """Calculate the height of the bounding box."""
        return self.y2 - self.y1


@dataclass
class Detection:
    """
    Represents a single face detection with recognition results.
    
    Attributes:
        bbox: Bounding box coordinates of the detected face
        name: Person's name if recognized, or "Unknown" if not recognized
        confidence: Recognition confidence score (0.0 to 1.0) from SVM classifier
        detection_confidence: Face detection confidence score (0.0 to 1.0)
    """
    bbox: BoundingBox
    name: str
    confidence: float
    detection_confidence: float


@dataclass
class VideoSession:
    """
    Represents a video streaming session.
    
    Attributes:
        session_id: Unique identifier for the session (UUID string)
        start_time: Timestamp when the session started
        frame_count: Number of frames processed in this session (default: 0)
    """
    session_id: str
    start_time: datetime
    frame_count: int = 0
