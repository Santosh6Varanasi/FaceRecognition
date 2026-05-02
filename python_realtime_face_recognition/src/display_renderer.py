"""
Display renderer component for the Python real-time face recognition application.

This module provides the DisplayRenderer class responsible for:
- Creating and managing the display window
- Rendering video frames with detection overlays
- Drawing bounding boxes and labels for detected faces
- Displaying FPS counter
- Handling user input for application exit
"""

import cv2
import numpy as np
from typing import List, Optional
from .models import Detection


class DisplayRenderer:
    """
    Handles display window management and frame rendering with detection overlays.
    
    This class manages the OpenCV display window and provides methods for:
    - Displaying video frames
    - Drawing bounding boxes and labels for face detections
    - Adding FPS overlay
    - Detecting quit events (key press or window close)
    
    Attributes:
        window_name: Name of the display window
    """
    
    def __init__(self, window_name: str = "Face Recognition"):
        """
        Initialize the display renderer with a named window.
        
        Args:
            window_name: Name for the OpenCV display window (default: "Face Recognition")
        """
        self.window_name = window_name
        # Create the named window
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
    
    def show_frame(self, frame: np.ndarray) -> None:
        """
        Display a frame in the window using cv2.imshow.
        
        Args:
            frame: The frame to display (numpy array in BGR format)
        """
        if frame is not None and frame.size > 0:
            cv2.imshow(self.window_name, frame)
    
    def draw_detections(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """
        Draw bounding boxes and labels for detected faces on the frame.
        
        Draws:
        - Green boxes (0, 255, 0) for known faces (name != "Unknown")
        - Red boxes (0, 0, 255) for unknown faces (name == "Unknown")
        - Uses 2-pixel thickness for bounding boxes
        - Renders person name or "Unknown" above each bounding box
        - Adds semi-transparent background for label readability
        
        Args:
            frame: The frame to draw on (numpy array in BGR format)
            detections: List of Detection objects to render
        
        Returns:
            The modified frame with bounding boxes and labels drawn
        """
        if frame is None or frame.size == 0:
            return frame
        
        # Create a copy to avoid modifying the original frame
        output_frame = frame.copy()
        
        # Font settings for labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        
        for detection in detections:
            # Determine box color based on whether face is known or unknown
            if detection.name == "Unknown":
                color = (0, 0, 255)  # Red for unknown faces
            else:
                color = (0, 255, 0)  # Green for known faces
            
            # Draw the bounding box rectangle
            cv2.rectangle(
                output_frame,
                (detection.bbox.x1, detection.bbox.y1),
                (detection.bbox.x2, detection.bbox.y2),
                color,
                2  # 2-pixel thickness
            )
            
            # Prepare label text
            label = detection.name
            
            # Get text size for background rectangle
            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, font_thickness
            )
            
            # Calculate label position (above the bounding box)
            # Add padding for better readability and gap between label and box
            padding = 5
            gap = 3  # Gap between label background and bounding box
            label_x = detection.bbox.x1
            label_y = detection.bbox.y1 - padding - gap
            
            # Ensure label stays within frame bounds
            if label_y - text_height - padding < 0:
                # If label would go above frame, place it inside the box at the top
                label_y = detection.bbox.y1 + text_height + padding + gap
            
            # Calculate background rectangle coordinates
            bg_x1 = label_x
            bg_y1 = label_y - text_height - padding
            bg_x2 = label_x + text_width + padding * 2
            bg_y2 = label_y + padding
            
            # Ensure background rectangle stays within frame bounds
            bg_x1 = max(0, bg_x1)
            bg_y1 = max(0, bg_y1)
            bg_x2 = min(output_frame.shape[1], bg_x2)
            bg_y2 = min(output_frame.shape[0], bg_y2)
            
            # Create semi-transparent background for label
            # Use alpha blending for transparency
            overlay = output_frame.copy()
            cv2.rectangle(
                overlay,
                (bg_x1, bg_y1),
                (bg_x2, bg_y2),
                (0, 0, 0),  # Black background
                -1  # Filled rectangle
            )
            
            # Blend the overlay with the original frame (0.6 opacity for background)
            alpha = 0.6
            cv2.addWeighted(overlay, alpha, output_frame, 1 - alpha, 0, output_frame)
            
            # Draw the label text on top of the background
            text_x = label_x + padding
            text_y = label_y
            cv2.putText(
                output_frame,
                label,
                (text_x, text_y),
                font,
                font_scale,
                (255, 255, 255),  # White text
                font_thickness,
                cv2.LINE_AA  # Anti-aliased for better quality
            )
        
        return output_frame
    
    def add_fps_overlay(self, frame: np.ndarray, fps: float) -> np.ndarray:
        """
        Add FPS counter overlay to the frame in the top-left corner.
        
        Displays the FPS counter with:
        - White text for visibility
        - Black background rectangle for contrast
        - Positioned in top-left corner with padding
        
        Args:
            frame: The frame to add FPS overlay to (numpy array in BGR format)
            fps: The current frames per second value
        
        Returns:
            The modified frame with FPS overlay
        """
        if frame is None or frame.size == 0:
            return frame
        
        # Create a copy to avoid modifying the original frame
        output_frame = frame.copy()
        
        # Format FPS text
        fps_text = f"FPS: {fps:.1f}"
        
        # Font settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        
        # Get text size for background rectangle
        (text_width, text_height), baseline = cv2.getTextSize(
            fps_text, font, font_scale, font_thickness
        )
        
        # Position in top-left corner with padding
        padding = 10
        text_x = padding
        text_y = padding + text_height
        
        # Calculate background rectangle coordinates
        bg_x1 = padding
        bg_y1 = padding
        bg_x2 = padding + text_width + padding
        bg_y2 = padding + text_height + padding
        
        # Draw black background rectangle
        cv2.rectangle(
            output_frame,
            (bg_x1, bg_y1),
            (bg_x2, bg_y2),
            (0, 0, 0),  # Black background
            -1  # Filled rectangle
        )
        
        # Draw white text on top of the background
        cv2.putText(
            output_frame,
            fps_text,
            (text_x, text_y),
            font,
            font_scale,
            (255, 255, 255),  # White text
            font_thickness,
            cv2.LINE_AA  # Anti-aliased for better quality
        )
        
        return output_frame
    
    def should_quit(self) -> bool:
        """
        Check if the user wants to quit the application.
        
        Checks for:
        - 'q' key press
        - Window close event (clicking X button)
        
        Returns:
            True if the user wants to quit, False otherwise
        """
        # Wait for 1ms and check for key press
        key = cv2.waitKey(1) & 0xFF
        
        # Check if 'q' key was pressed
        if key == ord('q'):
            return True
        
        # Check if window was closed (getWindowProperty returns -1 if window is closed)
        try:
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                return True
        except cv2.error:
            # Window doesn't exist or was closed
            return True
        
        return False
    
    def __del__(self):
        """
        Cleanup: destroy the window when the renderer is deleted.
        """
        try:
            cv2.destroyWindow(self.window_name)
        except:
            pass  # Ignore errors during cleanup
