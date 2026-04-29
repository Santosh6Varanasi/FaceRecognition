"""
Video processor service — extract frames from a video file and run face inference.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
import uuid
import logging
import hashlib
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from werkzeug.datastructures import FileStorage

from services import inference_service
from db import queries

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    """Video metadata extracted from file."""
    id: int
    filename: str
    file_path: str
    duration: float
    frame_count: int
    fps: float
    resolution: tuple[int, int]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    reprocessed_at: Optional[datetime]
    model_version: Optional[int]
    status: str


class VideoProcessorService:
    """Service for handling video upload, processing, and metadata extraction."""
    
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}
    UPLOAD_FOLDER = 'video_uploads'
    FRAME_EXTRACTION_FPS = 1  # Extract 1 frame per second
    
    def __init__(self, db_connection):
        """Initialize the video processor service.
        
        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
        
        # Ensure upload folder exists
        if not os.path.exists(self.UPLOAD_FOLDER):
            os.makedirs(self.UPLOAD_FOLDER)
    
    def _validate_video_format(self, filename: str) -> bool:
        """Validate video file format.
        
        Args:
            filename: Name of the video file
            
        Returns:
            True if format is valid, False otherwise
        """
        if '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.ALLOWED_EXTENSIONS
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Hex digest of the file hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _extract_video_metadata(self, file_path: str) -> Dict:
        """Extract video metadata using OpenCV.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dictionary containing duration, fps, resolution, frame_count
            
        Raises:
            ValueError: If video file cannot be opened or metadata extraction fails
        """
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {file_path}")
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate duration in seconds
            duration = total_frames / fps if fps > 0 else 0
            
            return {
                'duration': duration,
                'fps': fps,
                'resolution': (width, height),
                'frame_count': total_frames,
                'width': width,
                'height': height
            }
        finally:
            cap.release()
    
    def upload_video(self, file: FileStorage, user_id: Optional[int] = None) -> VideoMetadata:
        """Upload and store video file with metadata extraction.
        
        Args:
            file: FileStorage object from Flask request
            user_id: Optional user ID who uploaded the video
            
        Returns:
            VideoMetadata object with extracted metadata
            
        Raises:
            ValueError: If file format is invalid or metadata extraction fails
        """
        # Validate file
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        if not self._validate_video_format(file.filename):
            raise ValueError(
                f"Invalid video format. Allowed formats: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Generate unique filename to avoid collisions
        original_filename = file.filename
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        file_path = os.path.join(self.UPLOAD_FOLDER, unique_filename)
        
        # Save file to disk
        file.save(file_path)
        logger.info(f"Saved video file to: {file_path}")
        
        try:
            # Calculate file hash for deduplication
            video_hash = self._calculate_file_hash(file_path)
            
            # Check if video already exists
            existing_video = queries.get_video_by_hash(self.db, video_hash)
            if existing_video:
                # Remove duplicate file
                os.remove(file_path)
                logger.info(f"Video already exists with hash: {video_hash}")
                
                # Return existing video metadata
                return VideoMetadata(
                    id=existing_video['id'],
                    filename=existing_video['filename'],
                    file_path=existing_video['file_path'],
                    duration=existing_video['duration_seconds'] or 0,
                    frame_count=0,  # Not stored in current schema
                    fps=existing_video['fps'] or 0,
                    resolution=(existing_video['width'] or 0, existing_video['height'] or 0),
                    uploaded_at=existing_video['uploaded_at'],
                    processed_at=existing_video['last_processed_at'],
                    reprocessed_at=None,  # Not in current schema
                    model_version=None,  # Not in current schema
                    status=existing_video['status']
                )
            
            # Extract video metadata using OpenCV
            metadata = self._extract_video_metadata(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Store video metadata in database
            video_id = queries.insert_video(
                self.db,
                filename=original_filename,
                file_path=file_path,
                file_size_bytes=file_size,
                video_hash=video_hash,
                duration_seconds=metadata['duration'],
                fps=metadata['fps'],
                width=metadata['width'],
                height=metadata['height']
            )
            
            logger.info(f"Video uploaded successfully: ID={video_id}, filename={original_filename}")
            
            # Return VideoMetadata object
            return VideoMetadata(
                id=video_id,
                filename=original_filename,
                file_path=file_path,
                duration=metadata['duration'],
                frame_count=metadata['frame_count'],
                fps=metadata['fps'],
                resolution=metadata['resolution'],
                uploaded_at=datetime.utcnow(),
                processed_at=None,
                reprocessed_at=None,
                model_version=None,
                status='pending'
            )
            
        except Exception as e:
            # Clean up file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"Failed to upload video: {str(e)}")
            raise
    
    def process_video(self, video_id: int, job_id: str, file_path: str) -> None:
        """
        Extract frames from video at 1 FPS and run face detection on each frame.
        
        This function implements the frame extraction and face detection pipeline:
        1. Opens video file and extracts metadata (fps, duration, dimensions)
        2. Extracts frames at 1 FPS (1 frame per second)
        3. For each frame, calls FaceDetectionService (via inference_service) to detect faces
        4. Stores frame number and timestamp for each detection
        5. Handles batch processing for efficiency with progress updates every 10 frames
        
        Args:
            video_id: Database ID of the video being processed
            job_id: Unique identifier for this processing job
            file_path: Path to the video file on disk
        
        Requirements: 4.2, 8.1, 15.1
        """
        try:
            # Open video file
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                queries.update_video_job_status(self.db, job_id, 'failed', message='Cannot open video file')
                queries.update_video_record_status(self.db, video_id, 'failed')
                return

            # Extract video metadata
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_video_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration_seconds = total_video_frames / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Extract frames at 1 FPS (1000ms interval)
            # This ensures consistent frame extraction rate regardless of video FPS
            frame_interval_ms = 1000  # 1 FPS = 1 frame per second = 1000ms interval
            timestamps = list(range(0, int(duration_seconds * 1000), frame_interval_ms))
            total_frames = len(timestamps)

            logger.info(
                'Processing video %d: duration=%.2fs, fps=%.2f, resolution=%dx%d, extracting %d frames at 1 FPS',
                video_id, duration_seconds, fps, width, height, total_frames
            )

            # Create video session for tracking detections
            video_session_id = str(uuid.uuid4())
            queries.insert_video_session(self.db, video_session_id)

            # Update job status to running
            queries.update_video_job_status(
                self.db, job_id, 'running',
                total_frames=total_frames,
                video_session_id=video_session_id,
                message=f'Processing {total_frames} frames at 1 FPS...',
            )

            # Process each frame
            frames_processed = 0
            frames_skipped = 0
            
            for frame_number, timestamp_ms in enumerate(timestamps):
                # Seek to timestamp
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
                ret, frame_bgr = cap.read()
                
                if not ret:
                    logger.warning(
                        'Could not read frame %d at timestamp %d ms (job %s)',
                        frame_number, timestamp_ms, job_id
                    )
                    frames_skipped += 1
                    continue

                # Run face detection and recognition on frame
                # This calls FaceDetectionService internally and stores:
                # - Frame with frame_number and timestamp_ms
                # - Detections with bbox coordinates and recognition results
                # - Video detections in video_detections table
                # - Unknown faces with video source tracking (video_id, frame_timestamp, frame_number)
                try:
                    inference_service.run_inference(
                        frame_bgr, 
                        video_session_id, 
                        self.db, 
                        timestamp_ms=timestamp_ms,
                        video_id=video_id,
                        frame_number=frame_number
                    )
                    frames_processed += 1
                except Exception as frame_exc:
                    logger.warning(
                        'Failed to process frame %d at timestamp %d ms: %s',
                        frame_number, timestamp_ms, frame_exc
                    )
                    frames_skipped += 1
                    continue

                # Update progress every 10 frames or on last frame
                if frames_processed % 10 == 0 or frame_number == len(timestamps) - 1:
                    progress_pct = int((frame_number + 1) / total_frames * 100)
                    queries.update_video_job_status(
                        self.db, job_id, 'running',
                        progress_pct=progress_pct,
                        frames_processed=frames_processed,
                        total_frames=total_frames,
                        video_session_id=video_session_id,
                        message=f'Processing frame {frame_number + 1} of {total_frames} ({frames_processed} processed, {frames_skipped} skipped)...',
                    )

            # Release video capture
            cap.release()

            # Get face detection counts
            counts = queries.get_video_session_face_counts(self.db, video_session_id)

            logger.info(
                'Video %d processing complete: %d frames processed, %d skipped, %d unique unknown faces, %d unique known persons',
                video_id, frames_processed, frames_skipped, counts['unique_unknowns'], counts['unique_known']
            )

            # Update job status to completed
            queries.update_video_job_status(
                self.db, job_id, 'completed',
                progress_pct=100,
                frames_processed=frames_processed,
                total_frames=total_frames,
                video_session_id=video_session_id,
                message=f'Processing complete: {frames_processed} frames processed, {counts["unique_unknowns"]} unknown faces, {counts["unique_known"]} known persons',
                unique_unknowns=counts['unique_unknowns'],
                unique_known=counts['unique_known'],
            )

            # Update video record status
            queries.update_video_record_status(
                self.db, video_id, 'processed',
                last_processed_at=datetime.utcnow(),
                unique_unknowns=counts['unique_unknowns'],
                unique_known=counts['unique_known'],
            )

        except Exception as exc:
            logger.exception('Video processing failed for job %s', job_id)
            queries.update_video_job_status(self.db, job_id, 'failed', message=str(exc))
            queries.update_video_record_status(self.db, video_id, 'failed')
    
    def get_detections_at_timestamp(
        self, video_id: int, timestamp: float, tolerance: float = 0.25
    ) -> list:
        """
        Retrieve detections for a specific timestamp with tolerance window.
        
        This method queries the video_detections table for detections within
        the tolerance window (timestamp ± tolerance). Used by the frontend
        Detection Overlay component to fetch detections for the current
        playback position.
        
        Args:
            video_id: Database ID of the video
            timestamp: Target timestamp in seconds from video start
            tolerance: Tolerance window in seconds (default 0.25 = 250ms)
            
        Returns:
            List of detection dictionaries with keys:
            - person_id: person ID (or None for unknown)
            - person_name: person name or "Unknown"
            - bbox: dict with x1, y1, x2, y2 coordinates
            - recognition_confidence: face recognition confidence (0-1)
            - detection_confidence: face detection confidence (0-1)
            
        Requirements: 4.5, 15.1
        """
        detections = queries.get_detections_at_timestamp(
            self.db, video_id, timestamp, tolerance
        )
        
        logger.debug(
            f"Retrieved {len(detections)} detections for video {video_id} "
            f"at timestamp {timestamp}s (tolerance {tolerance}s)"
        )
        
        return detections
    
    def get_timeline(self, video_id: int) -> list:
        """
        Generate timeline entries from detection data by grouping consecutive detections by person.
        
        This method implements the timeline generation algorithm:
        1. Query video_detections table for the given video_id, ordered by frame_number
        2. Group detections by person (person_id/person_name)
        3. For each person, identify continuous segments (consecutive frame numbers)
        4. Split into separate entries when person is missing for at least one frame
        5. Calculate start_time (timestamp of first frame), end_time (timestamp of last frame)
        6. Calculate detection_count (number of detections in segment)
        7. Calculate avg_confidence (average recognition_confidence)
        8. Store each segment as a timeline_entry in the database
        9. Return list of timeline entries for the video
        
        Args:
            video_id: Database ID of the video
            
        Returns:
            List of timeline entry dictionaries with keys:
            - id: timeline entry ID
            - video_id: video ID
            - person_id: person ID (or None for unknown)
            - person_name: person name
            - start_time: segment start time in seconds
            - end_time: segment end time in seconds
            - detection_count: number of detections in segment
            - avg_confidence: average recognition confidence
            - created_at: timestamp when entry was created
            
        Requirements: 6.2, 6.3, 6.5, 14.2, 14.3
        """
        # Query all detections for this video, ordered by frame_number
        detections = queries.get_video_detections_for_timeline(self.db, video_id)
        
        if not detections:
            logger.info(f"No detections found for video {video_id}")
            return []
        
        # Group detections by person
        # Key: (person_id, person_name), Value: list of detections
        person_detections = {}
        for det in detections:
            key = (det['person_id'], det['person_name'])
            if key not in person_detections:
                person_detections[key] = []
            person_detections[key].append(det)
        
        # Generate timeline entries for each person
        timeline_entries = []
        
        for (person_id, person_name), person_dets in person_detections.items():
            # Sort by frame_number to ensure consecutive ordering
            person_dets.sort(key=lambda d: d['frame_number'])
            
            # Identify continuous segments (consecutive frame numbers)
            segments = []
            current_segment = [person_dets[0]]
            
            for i in range(1, len(person_dets)):
                prev_frame = person_dets[i - 1]['frame_number']
                curr_frame = person_dets[i]['frame_number']
                
                # Check if frames are consecutive (difference of 1)
                if curr_frame == prev_frame + 1:
                    # Continue current segment
                    current_segment.append(person_dets[i])
                else:
                    # Gap detected - save current segment and start new one
                    segments.append(current_segment)
                    current_segment = [person_dets[i]]
            
            # Add the last segment
            segments.append(current_segment)
            
            # Create timeline entry for each segment
            for segment in segments:
                start_time = segment[0]['timestamp']
                end_time = segment[-1]['timestamp']
                detection_count = len(segment)
                avg_confidence = sum(d['recognition_confidence'] for d in segment) / detection_count
                
                # Insert timeline entry into database
                entry_id = queries.insert_timeline_entry(
                    self.db,
                    video_id=video_id,
                    person_id=person_id,
                    person_name=person_name,
                    start_time=start_time,
                    end_time=end_time,
                    detection_count=detection_count,
                    avg_confidence=avg_confidence
                )
                
                timeline_entries.append({
                    'id': entry_id,
                    'video_id': video_id,
                    'person_id': person_id,
                    'person_name': person_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'detection_count': detection_count,
                    'avg_confidence': avg_confidence
                })
        
        logger.info(
            f"Generated {len(timeline_entries)} timeline entries for video {video_id} "
            f"({len(person_detections)} unique persons)"
        )
        
        return timeline_entries


    def reprocess_video(self, video_id: int, model_version: Optional[int] = None) -> Dict:
        """
        Reprocess video with updated model version.
        
        This method implements the video reprocessing workflow:
        1. Delete existing detections from video_detections table
        2. Delete existing timeline entries from timeline_entries table
        3. Get video file_path from videos table
        4. Create new job_id for tracking
        5. Call process_video() to re-analyze the video
        6. Update videos table with reprocessed_at = NOW() and model_version
        
        Args:
            video_id: Database ID of the video to reprocess
            model_version: Optional model version to use (defaults to active model)
            
        Returns:
            Dictionary with reprocessing status:
            - video_id: int
            - job_id: str
            - status: str ('queued', 'processing', 'completed', 'failed')
            - message: str
            
        Raises:
            ValueError: If video does not exist
            Exception: If reprocessing fails
            
        Requirements: 11.3, 12.1, 12.2
        """
        # Get video metadata
        video = queries.get_video_by_id(self.db, video_id)
        if not video:
            raise ValueError(f"Video with ID {video_id} does not exist")
        
        file_path = video['file_path']
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise ValueError(f"Video file not found: {file_path}")
        
        logger.info(f"Starting reprocessing for video {video_id} with model version {model_version}")
        
        try:
            # Delete existing detections and timeline entries
            db_conn = self.db.get_connection()
            try:
                cursor = db_conn.cursor()
                
                # Delete timeline entries first (no foreign key dependencies)
                cursor.execute(
                    "DELETE FROM timeline_entries WHERE video_id = %s",
                    (video_id,)
                )
                deleted_timeline = cursor.rowcount
                
                # Delete video detections
                cursor.execute(
                    "DELETE FROM video_detections WHERE video_id = %s",
                    (video_id,)
                )
                deleted_detections = cursor.rowcount
                
                db_conn.commit()
                logger.info(
                    f"Deleted {deleted_detections} detections and {deleted_timeline} "
                    f"timeline entries for video {video_id}"
                )
            except Exception as e:
                db_conn.rollback()
                raise Exception(f"Failed to delete existing data: {str(e)}")
            finally:
                cursor.close()
                self.db.return_connection(db_conn)
            
            # Create new job for reprocessing
            job_id = str(uuid.uuid4())
            queries.insert_video_job(self.db, job_id, video_id)
            logger.info(f"Created reprocessing job {job_id} for video {video_id}")
            
            # Update video status to processing
            queries.update_video_record_status(self.db, video_id, 'processing')
            
            # Process video (this will run face detection and recognition)
            self.process_video(video_id, job_id, file_path)
            
            # Get active model version if not specified
            if model_version is None:
                active_model = queries.get_active_model_version(self.db)
                if active_model:
                    model_version = active_model['version_number']
            
            # Update video record with reprocessed_at and model_version
            db_conn = self.db.get_connection()
            try:
                cursor = db_conn.cursor()
                cursor.execute(
                    "UPDATE videos SET reprocessed_at = NOW(), model_version = %s WHERE id = %s",
                    (model_version, video_id)
                )
                db_conn.commit()
                logger.info(
                    f"Updated video {video_id} with reprocessed_at and model_version {model_version}"
                )
            except Exception as e:
                db_conn.rollback()
                raise Exception(f"Failed to update video metadata: {str(e)}")
            finally:
                cursor.close()
                self.db.return_connection(db_conn)
            
            return {
                'video_id': video_id,
                'job_id': job_id,
                'status': 'completed',
                'message': f'Video reprocessed successfully with model version {model_version}',
                'model_version': model_version
            }
            
        except Exception as e:
            logger.exception(f"Failed to reprocess video {video_id}")
            # Update video status to failed
            queries.update_video_record_status(self.db, video_id, 'failed')
            raise


def process_video(video_id: int, job_id: str, file_path: str, db) -> None:
    """
    Standalone wrapper for VideoProcessorService.process_video() method.
    
    This function maintains backward compatibility for existing code that calls
    the standalone process_video() function. It creates a VideoProcessorService
    instance and delegates to the instance method.
    
    Args:
        video_id: Database ID of the video being processed
        job_id: Unique identifier for this processing job
        file_path: Path to the video file on disk
        db: Database connection instance
    
    Requirements: 4.2, 8.1, 15.1
    """
    service = VideoProcessorService(db)
    service.process_video(video_id, job_id, file_path)


def generate_video_with_bounding_boxes(video_id: int, file_path: str, db) -> str:
    """
    Generate a video with bounding boxes and labels overlaid on detected faces.
    
    Args:
        video_id: ID of the video to process
        file_path: Path to the original video file
        db: Database connection
    
    Returns:
        Path to the generated video file with bounding boxes
    
    Raises:
        Exception if video generation fails
    """
    import tempfile
    
    # Read original video
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise Exception(f"Cannot open video file: {file_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    # Create temporary output file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    output_path = temp_file.name
    temp_file.close()
    
    # Create video writer
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Get all detections for this video
    detections = queries.get_video_detections_with_frames(db, video_id)
    
    # Group detections by frame number
    detections_by_frame = {}
    for det in detections:
        frame_num = det["frame_number"]
        if frame_num not in detections_by_frame:
            detections_by_frame[frame_num] = []
        detections_by_frame[frame_num].append(det)
    
    # Process each frame
    frame_number = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Draw bounding boxes for this frame
        if frame_number in detections_by_frame:
            for det in detections_by_frame[frame_number]:
                x1 = det["bbox_x1"]
                y1 = det["bbox_y1"]
                x2 = det["bbox_x2"]
                y2 = det["bbox_y2"]
                name = det["person_name"]
                confidence = det["confidence"]
                
                # Choose color: green for known, red for unknown
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label with name and confidence
                label = f"{name} ({confidence:.2f})"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                label_y = max(y1 - 10, label_size[1])
                
                # Draw label background
                cv2.rectangle(frame, (x1, label_y - label_size[1] - 5), 
                             (x1 + label_size[0], label_y + 5), color, -1)
                
                # Draw label text
                cv2.putText(frame, label, (x1, label_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Write frame to output video
        out.write(frame)
        frame_number += 1
    
    # Release resources
    cap.release()
    out.release()
    
    logger.info(f"Generated video with bounding boxes: {output_path}")
    return output_path
