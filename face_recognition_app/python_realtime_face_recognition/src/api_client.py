"""
API client for communicating with the Flask API backend.

This module provides the APIClient class that handles:
- Session management (start/end video sessions)
- Frame processing (sending frames for inference)
- HTTP error handling and retries
- Response parsing into Detection objects
"""

import base64
import logging
import time
from typing import Dict, List, Optional

import cv2
import numpy as np
import requests

from .models import BoundingBox, Detection


logger = logging.getLogger(__name__)


class APIClient:
    """
    Client for communicating with the Flask API backend.
    
    Handles session management, frame encoding, HTTP requests,
    and response parsing for face recognition inference.
    
    Attributes:
        base_url: Base URL of the Flask API (e.g., "http://localhost:5000")
        timeout: HTTP request timeout in seconds
    """
    
    def __init__(self, base_url: str, timeout: int = 5):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the Flask API backend
            timeout: HTTP request timeout in seconds (default: 5)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._session = requests.Session()
    
    def start_session(self) -> Optional[str]:
        """
        Create a new video session with the Flask API.
        
        Calls POST /api/stream/session/start to create a session
        and returns the session_id UUID.
        
        Returns:
            Session ID (UUID string) if successful, None on failure
        """
        url = f"{self.base_url}/api/stream/session/start"
        
        try:
            response = self._session.post(url, json={}, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            session_id = data.get("session_id")
            
            if session_id:
                logger.info(f"Session started: {session_id}")
                return session_id
            else:
                logger.error("Session start response missing session_id")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Session start timeout after {self.timeout}s")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Session start connection error: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Session start HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Session start unexpected error: {e}")
            return None
    
    def end_session(self, session_id: str, total_frames: int) -> bool:
        """
        End a video session with the Flask API.
        
        Calls POST /api/stream/session/end to mark the session as complete
        with the total frame count.
        
        Args:
            session_id: UUID of the session to end
            total_frames: Total number of frames processed in the session
        
        Returns:
            True if successful, False on failure
        """
        url = f"{self.base_url}/api/stream/session/end"
        
        try:
            payload = {
                "session_id": session_id,
                "total_frames": total_frames
            }
            
            response = self._session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            logger.info(f"Session ended: {session_id} ({total_frames} frames)")
            return True
            
        except requests.exceptions.Timeout:
            logger.warning(f"Session end timeout after {self.timeout}s")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Session end connection error: {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Session end HTTP error: {e}")
            return False
        except Exception as e:
            logger.warning(f"Session end unexpected error: {e}")
            return False
    
    def process_frame(self, session_id: str, frame: np.ndarray) -> Optional[List[Detection]]:
        """
        Send a frame to the Flask API for face detection and recognition.
        
        Encodes the frame as base64 JPEG, sends it to POST /api/stream/frame,
        and parses the response into Detection objects.
        
        Implements retry logic with exponential backoff (3 attempts).
        
        Args:
            session_id: UUID of the current video session
            frame: BGR frame as numpy array
        
        Returns:
            List of Detection objects if successful, None on failure
        """
        # Encode frame as base64 JPEG
        frame_data = self._encode_frame(frame)
        if frame_data is None:
            return None
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                detections = self._send_frame_request(session_id, frame_data)
                if detections is not None:
                    return detections
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API timeout (attempt {attempt + 1}/{max_retries})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"API connection failed (attempt {attempt + 1}/{max_retries})")
            except requests.exceptions.HTTPError as e:
                logger.warning(f"API HTTP error (attempt {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                logger.error(f"API unexpected error (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Exponential backoff before retry
            if attempt < max_retries - 1:
                backoff_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                time.sleep(backoff_time)
        
        # All retries failed
        logger.error(f"Frame processing failed after {max_retries} attempts")
        return None
    
    def _encode_frame(self, frame: np.ndarray, quality: int = 85) -> Optional[str]:
        """
        Encode a frame as base64 JPEG string.
        
        Args:
            frame: BGR frame as numpy array
            quality: JPEG compression quality (0-100, default: 85)
        
        Returns:
            Base64-encoded JPEG string if successful, None on failure
        """
        try:
            if frame is None or frame.size == 0:
                logger.warning("Empty frame, skipping encoding")
                return None
            
            # Encode as JPEG with specified quality
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not success:
                logger.warning("Frame encoding failed")
                return None
            
            # Convert to base64 string
            frame_data = base64.b64encode(buffer).decode('utf-8')
            return frame_data
            
        except Exception as e:
            logger.error(f"Frame encoding error: {e}")
            return None
    
    def _send_frame_request(self, session_id: str, frame_data: str) -> Optional[List[Detection]]:
        """
        Send frame data to the API and parse the response.
        
        Args:
            session_id: UUID of the current video session
            frame_data: Base64-encoded JPEG frame
        
        Returns:
            List of Detection objects if successful, None on failure
        """
        url = f"{self.base_url}/api/stream/frame"
        
        payload = {
            "session_id": session_id,
            "frame_data": frame_data
        }
        
        response = self._session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        detections_data = data.get("detections", [])
        
        # Convert to Detection objects
        detections = self._parse_detections(detections_data)
        
        # Log processing info
        processing_time = data.get("processing_time_ms", 0)
        logger.debug(f"Frame processed: {len(detections)} faces detected ({processing_time:.0f}ms)")
        
        return detections
    
    def _parse_detections(self, detections_data: List[Dict]) -> List[Detection]:
        """
        Parse detection data from API response into Detection objects.
        
        Args:
            detections_data: List of detection dictionaries from API response
        
        Returns:
            List of Detection objects
        """
        detections = []
        
        for det_data in detections_data:
            try:
                # Parse bounding box
                bbox_data = det_data.get("bbox", {})
                bbox = BoundingBox(
                    x1=int(bbox_data.get("x1", 0)),
                    y1=int(bbox_data.get("y1", 0)),
                    x2=int(bbox_data.get("x2", 0)),
                    y2=int(bbox_data.get("y2", 0))
                )
                
                # Parse detection fields
                name = det_data.get("name", "Unknown")
                confidence = float(det_data.get("confidence", 0.0))
                detection_confidence = float(det_data.get("detection_confidence", 0.0))
                
                detection = Detection(
                    bbox=bbox,
                    name=name,
                    confidence=confidence,
                    detection_confidence=detection_confidence
                )
                
                detections.append(detection)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse detection: {e}")
                continue
        
        return detections
