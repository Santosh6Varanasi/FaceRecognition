"""
Annotated Video Generator Service

This service generates videos with bounding boxes and labels burned directly into frames.
It reads the original video, queries detection data from the database, and creates a new
video file with visual annotations overlaid on each frame.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 12.2, 12.3, 12.4
"""

import cv2
import numpy as np
import logging
import os
import time
from typing import Dict, List, Any, Optional

from face_recognition_app.database.db_connection import DatabaseConnection
from face_recognition_app.flask_api.db import queries

# Set up logger
logger = logging.getLogger(__name__)

# Color constants (BGR format for OpenCV)
COLOR_KNOWN_PERSON = (94, 197, 34)  # Green #22c55e
COLOR_UNKNOWN_PERSON = (68, 68, 239)  # Red #ef4444
COLOR_TEXT = (255, 255, 255)  # White

# Bounding box rendering constants
BBOX_LINE_WIDTH = 2
LABEL_FONT = cv2.FONT_HERSHEY_SIMPLEX
LABEL_FONT_SCALE = 0.5
LABEL_FONT_THICKNESS = 1
LABEL_PADDING_X = 5
LABEL_PADDING_Y = 6
LABEL_OFFSET_Y = 22  # Position label above bbox


class AnnotatedVideoGenerator:
    """Service for generating videos with bounding boxes overlaid."""
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the annotated video generator.
        
        Args:
            db_connection: Database connection for querying detection data
        """
        self.db = db_connection
        logger.info("AnnotatedVideoGenerator initialized")
    
    def generate(
        self,
        video_id: int,
        original_video_path: str,
        output_video_path: str,
    ) -> Dict[str, Any]:
        """
        Generate annotated video with bounding boxes.
        
        Args:
            video_id: Database ID of the video
            original_video_path: Path to original video file
            output_video_path: Path where annotated video should be saved
            
        Returns:
            Dictionary with generation metadata:
            - output_path: str (path to generated video)
            - frame_count: int (number of frames processed)
            - duration_seconds: float (time taken to generate)
            - file_size_bytes: int (size of generated file)
            
        Raises:
            ValueError: If original video cannot be opened or validation fails
            IOError: If output path is not writable
            Exception: If generation fails
        
        Requirements: 3.1, 3.5, 3.6, 10.2, 11.1, 11.2, 11.3
        """
        start_time = time.time()
        logger.info(f"Starting annotated video generation for video_id={video_id}")
        
        # Validate inputs
        if not os.path.exists(original_video_path):
            error_msg = f"Original video not found: {original_video_path}"
            logger.error(f"video_id={video_id}: {error_msg}")
            raise ValueError(error_msg)
        
        output_dir = os.path.dirname(output_video_path)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                error_msg = f"Cannot create output directory: {output_dir}"
                logger.error(f"video_id={video_id}: {error_msg} - {str(e)}")
                raise IOError(error_msg)
        
        if not os.access(output_dir, os.W_OK):
            error_msg = f"Output directory not writable: {output_dir}"
            logger.error(f"video_id={video_id}: {error_msg}")
            raise IOError(error_msg)
        
        # Open original video
        cap = cv2.VideoCapture(original_video_path)
        if not cap.isOpened():
            error_msg = f"Cannot open video file: {original_video_path}"
            logger.error(f"video_id={video_id}: {error_msg}")
            raise ValueError(error_msg)
        
        writer = None
        frames_processed = 0
        
        try:
            # Extract video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"video_id={video_id}: Video properties - {width}x{height} @ {fps}fps, {total_frames} frames")
            
            # Query all detections for this video from database
            logger.info(f"video_id={video_id}: Querying detections from database...")
            detections_by_frame = self._load_detections(video_id)
            logger.info(f"video_id={video_id}: Loaded detections for {len(detections_by_frame)} frames")
            
            # Initialize video writer with same codec as original
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            # Fallback to MP4V if original codec fails
            try:
                writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
                if not writer.isOpened():
                    logger.warning(f"video_id={video_id}: Original codec failed, falling back to MP4V")
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
            except Exception as e:
                logger.warning(f"video_id={video_id}: Codec error, using MP4V - {str(e)}")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
            
            if not writer.isOpened():
                raise IOError(f"Cannot create video writer for: {output_video_path}")
            
            # Process frames
            frame_number = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Draw bounding boxes for this frame
                if frame_number in detections_by_frame:
                    for detection in detections_by_frame[frame_number]:
                        self._draw_bounding_box(
                            frame=frame,
                            bbox=detection['bbox'],
                            label=detection['label'],
                            confidence=detection['confidence'],
                            is_known=detection['is_known'],
                        )
                
                # Write frame to output video
                writer.write(frame)
                frames_processed += 1
                frame_number += 1
                
                # Log progress every 100 frames
                if frames_processed % 100 == 0:
                    logger.debug(f"video_id={video_id}: Processed {frames_processed}/{total_frames} frames")
            
            # Verify frame count preservation
            if frames_processed != total_frames:
                logger.warning(
                    f"video_id={video_id}: Frame count mismatch - "
                    f"processed {frames_processed}, expected {total_frames}"
                )
            
            generation_time = time.time() - start_time
            file_size = os.path.getsize(output_video_path)
            
            logger.info(
                f"video_id={video_id}: Annotated video generated successfully - "
                f"{frames_processed} frames in {generation_time:.2f}s, size={file_size} bytes"
            )
            
            return {
                "output_path": output_video_path,
                "frame_count": frames_processed,
                "duration_seconds": generation_time,
                "file_size_bytes": file_size,
            }
            
        except Exception as e:
            logger.exception(f"video_id={video_id}: Error generating annotated video")
            # Clean up partial output file
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                    logger.info(f"video_id={video_id}: Cleaned up partial output file")
                except Exception as cleanup_error:
                    logger.error(f"video_id={video_id}: Failed to clean up partial file - {str(cleanup_error)}")
            raise
            
        finally:
            # Always release resources
            cap.release()
            if writer is not None:
                writer.release()
            logger.debug(f"video_id={video_id}: Released video resources")
    
    def _load_detections(self, video_id: int) -> Dict[int, List[Dict]]:
        """
        Load all detections for a video from database and group by frame number.
        
        Args:
            video_id: Video ID to query
            
        Returns:
            Dictionary mapping frame_number to list of detection dicts
            Each detection dict contains: bbox, label, confidence, is_known
        
        Requirements: 2.6, 3.1
        """
        # Query detections from video_detections table with bbox coordinates
        detections = queries.get_video_detections_for_annotation(self.db, video_id)
        
        # Group by frame_number
        detections_by_frame: Dict[int, List[Dict]] = {}
        
        for det in detections:
            frame_num = det['frame_number']
            confidence = det['recognition_confidence']
            person_name = det['person_name']
            
            # Determine if this is a known person (confidence >= 0.5)
            is_known = confidence >= 0.5
            
            # Format label
            if is_known:
                label = f"{person_name} {int(confidence * 100)}%"
            else:
                label = "Unknown"
            
            # Create detection dict with bbox coordinates
            detection_dict = {
                'bbox': {
                    'x1': det['bbox_x1'],
                    'y1': det['bbox_y1'],
                    'x2': det['bbox_x2'],
                    'y2': det['bbox_y2'],
                },
                'label': label,
                'confidence': confidence,
                'is_known': is_known,
            }
            
            if frame_num not in detections_by_frame:
                detections_by_frame[frame_num] = []
            
            detections_by_frame[frame_num].append(detection_dict)
        
        return detections_by_frame
    
    def _draw_bounding_box(
        self,
        frame: np.ndarray,
        bbox: Dict[str, int],
        label: str,
        confidence: float,
        is_known: bool,
    ) -> None:
        """
        Draw a single bounding box with label on frame.
        
        Args:
            frame: OpenCV frame (BGR format)
            bbox: Dictionary with x1, y1, x2, y2 coordinates
            label: Person name or "Unknown"
            confidence: Recognition confidence (0-1)
            is_known: True if confidence >= 0.5, False otherwise
            
        Modifies frame in-place.
        
        Requirements: 3.2, 3.3, 3.4, 12.2, 12.3, 12.4
        """
        # Validate bounding box
        frame_height, frame_width = frame.shape[:2]
        if not self._validate_bbox(bbox, frame_width, frame_height):
            logger.debug(f"Skipping invalid bounding box: {bbox}")
            return
        
        # Extract coordinates
        x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
        
        # Clip coordinates to frame bounds
        x1 = max(0, min(x1, frame_width - 1))
        y1 = max(0, min(y1, frame_height - 1))
        x2 = max(0, min(x2, frame_width))
        y2 = max(0, min(y2, frame_height))
        
        # Select color based on known/unknown status
        box_color = COLOR_KNOWN_PERSON if is_known else COLOR_UNKNOWN_PERSON
        
        # Draw bounding box rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, BBOX_LINE_WIDTH)
        
        # Calculate label dimensions
        (label_width, label_height), baseline = cv2.getTextSize(
            label, LABEL_FONT, LABEL_FONT_SCALE, LABEL_FONT_THICKNESS
        )
        
        # Calculate label position (above bounding box)
        label_x = x1
        label_y = y1 - LABEL_OFFSET_Y
        
        # Ensure label stays within frame bounds
        if label_y < 0:
            label_y = y2 + LABEL_OFFSET_Y  # Place below bbox if no room above
        
        # Draw label background rectangle
        bg_x1 = label_x
        bg_y1 = label_y - label_height - LABEL_PADDING_Y
        bg_x2 = label_x + label_width + 2 * LABEL_PADDING_X
        bg_y2 = label_y + baseline + LABEL_PADDING_Y
        
        cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), box_color, -1)
        
        # Draw label text
        text_x = label_x + LABEL_PADDING_X
        text_y = label_y
        cv2.putText(
            frame, label, (text_x, text_y),
            LABEL_FONT, LABEL_FONT_SCALE, COLOR_TEXT,
            LABEL_FONT_THICKNESS, cv2.LINE_AA
        )
    
    def _validate_bbox(
        self,
        bbox: Dict[str, int],
        frame_width: int,
        frame_height: int,
    ) -> bool:
        """
        Validate bounding box coordinates.
        
        Args:
            bbox: Dictionary with x1, y1, x2, y2 coordinates
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            
        Returns:
            True if bbox is valid, False otherwise
            
        Validation rules:
        - x2 > x1 and y2 > y1 (valid rectangle)
        - 0 <= x1 < x2 <= frame_width (within horizontal bounds)
        - 0 <= y1 < y2 <= frame_height (within vertical bounds)
        - width >= 10 and height >= 10 (minimum size)
        
        Requirements: 12.2, 12.3, 12.4
        """
        try:
            x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
            
            # Check valid rectangle
            if x2 <= x1 or y2 <= y1:
                return False
            
            # Check within bounds (allow some tolerance for clipping)
            if x1 < -10 or x2 > frame_width + 10:
                return False
            if y1 < -10 or y2 > frame_height + 10:
                return False
            
            # Check minimum size
            width = x2 - x1
            height = y2 - y1
            if width < 10 or height < 10:
                return False
            
            return True
            
        except (KeyError, TypeError) as e:
            logger.warning(f"Invalid bbox format: {bbox} - {str(e)}")
            return False
