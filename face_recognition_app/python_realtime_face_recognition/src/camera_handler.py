"""Camera handler component for capturing video frames.

This module provides the CameraHandler class that manages camera device
initialization, frame capture, and resource cleanup using OpenCV.
"""

import logging
from typing import Optional

import cv2
import numpy as np


logger = logging.getLogger(__name__)


class CameraHandler:
    """Handles camera device initialization and frame capture.
    
    This class provides a simple interface for accessing camera devices,
    capturing frames, and managing camera resources. It uses OpenCV's
    VideoCapture for camera I/O operations.
    
    Attributes:
        camera_index: Camera device index (0 for default camera)
        width: Frame width in pixels
        height: Frame height in pixels
    """
    
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        """Initialize camera handler with device and resolution settings.
        
        Args:
            camera_index: Camera device index (default: 0)
            width: Frame width in pixels (default: 640)
            height: Frame height in pixels (default: 480)
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self._capture: Optional[cv2.VideoCapture] = None
    
    def initialize(self) -> bool:
        """Initialize the camera device and set resolution.
        
        Opens the camera device using OpenCV VideoCapture and configures
        the frame resolution. If initialization fails, logs an error with
        troubleshooting tips.
        
        Returns:
            True if camera initialized successfully, False otherwise
        """
        try:
            self._capture = cv2.VideoCapture(self.camera_index)
            
            if not self._capture.isOpened():
                logger.error(f"Failed to open camera device {self.camera_index}")
                logger.info("Troubleshooting tips:")
                logger.info("  - Check camera is connected")
                logger.info("  - Close other applications using the camera")
                logger.info("  - Try a different camera index (0, 1, 2...)")
                self._capture = None
                return False
            
            # Set frame resolution
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # Verify resolution was set (some cameras may not support requested resolution)
            actual_width = self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            if actual_width != self.width or actual_height != self.height:
                logger.warning(
                    f"Requested resolution {self.width}x{self.height} not available. "
                    f"Using {int(actual_width)}x{int(actual_height)} instead."
                )
            
            logger.info(
                f"Camera {self.camera_index} initialized successfully "
                f"({int(actual_width)}x{int(actual_height)})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Exception during camera initialization: {e}")
            self._capture = None
            return False
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame from the camera.
        
        Reads the next available frame from the camera device. If the
        capture fails, logs a warning and returns None.
        
        Returns:
            Numpy array containing the frame in BGR format, or None if
            capture fails or camera is not initialized
        """
        if self._capture is None or not self._capture.isOpened():
            logger.warning("Cannot read frame: camera not initialized or closed")
            return None
        
        try:
            ret, frame = self._capture.read()
            
            if not ret or frame is None:
                logger.warning("Failed to capture frame from camera")
                return None
            
            return frame
            
        except Exception as e:
            logger.warning(f"Exception during frame capture: {e}")
            return None
    
    def release(self) -> None:
        """Release camera resources and close the device.
        
        Properly closes the camera device and releases associated resources.
        This method should be called when the camera is no longer needed,
        typically during application shutdown.
        """
        if self._capture is not None:
            try:
                self._capture.release()
                logger.info(f"Camera {self.camera_index} released successfully")
            except Exception as e:
                logger.error(f"Exception during camera release: {e}")
            finally:
                self._capture = None
    
    def is_opened(self) -> bool:
        """Check if the camera device is currently open.
        
        Returns:
            True if camera is initialized and open, False otherwise
        """
        return self._capture is not None and self._capture.isOpened()
