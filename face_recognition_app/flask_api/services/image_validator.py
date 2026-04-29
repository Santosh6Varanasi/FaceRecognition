"""
Image Validator Service — validates uploaded images contain exactly one face.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import time
import uuid
from typing import Dict, Optional

import cv2
import numpy as np
from deepface import DeepFace
from sklearn.preprocessing import normalize

from config import config

logger = logging.getLogger(__name__)


class ImageValidator:
    """
    Service for validating uploaded training images.
    Ensures each image contains exactly one detectable face.
    """

    def __init__(self):
        self.detector_backend = config.TRAINING_DETECTOR_BACKEND
        self.recognition_model = config.RECOGNITION_MODEL
        self._cache: Dict[str, dict] = {}

    def validate_single_face(self, frame_bgr: np.ndarray) -> dict:
        """
        Validate image contains exactly one face.

        Args:
            frame_bgr: Image as numpy array in BGR format

        Returns:
            dict with keys: image_id, image_path, face_bbox, detection_confidence, embedding

        Raises:
            ValueError: If validation fails (no face, multiple faces, or detection error)
        """
        try:
            # 1. Detect faces using configured detector
            face_objs = DeepFace.extract_faces(
                img_path=frame_bgr,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True,
            )

            # Filter low-confidence detections
            face_objs = [f for f in face_objs if f.get("confidence", 0) > 0.5]

            # 2. Validate exactly one face
            if len(face_objs) == 0:
                raise ValueError("No face detected in image")

            if len(face_objs) > 1:
                raise ValueError(
                    "Multiple faces detected, please upload images with only one face"
                )

            face_obj = face_objs[0]

            # 3. Extract bounding box
            area = face_obj.get("facial_area", {})
            bbox = {
                "x1": int(area.get("x", 0)),
                "y1": int(area.get("y", 0)),
                "x2": int(area.get("x", 0) + area.get("w", 0)),
                "y2": int(area.get("y", 0) + area.get("h", 0)),
            }
            detection_confidence = float(face_obj.get("confidence", 1.0))

            # 4. Generate ArcFace embedding
            face_img = face_obj.get("face")
            if face_img is None:
                raise ValueError("Failed to extract face image")

            # Convert to uint8 BGR
            if face_img.dtype != np.uint8:
                face_img_bgr = (face_img[:, :, ::-1] * 255).astype(np.uint8)
            else:
                face_img_bgr = face_img[:, :, ::-1]

            repr_objs = DeepFace.represent(
                img_path=face_img_bgr,
                model_name=self.recognition_model,
                detector_backend="skip",
                enforce_detection=False,
            )

            if not repr_objs:
                raise ValueError("Failed to generate face embedding")

            embedding = np.array(repr_objs[0]["embedding"], dtype=np.float64)
            embedding_norm = normalize(embedding.reshape(1, -1), norm="l2")[0]

            # 5. Save image to disk
            image_id = str(uuid.uuid4())
            os.makedirs(config.TRAINING_IMAGES_DIR, exist_ok=True)
            image_path = os.path.join(config.TRAINING_IMAGES_DIR, f"{image_id}.jpg")
            cv2.imwrite(image_path, frame_bgr)

            # 6. Store in cache
            self._cache[image_id] = {
                "embedding": embedding_norm,
                "image_path": image_path,
                "bbox": bbox,
                "detection_confidence": detection_confidence,
                "timestamp": time.time(),
            }

            logger.info(
                "Image validated successfully: image_id=%s, bbox=%s, confidence=%.2f",
                image_id,
                bbox,
                detection_confidence,
            )

            return {
                "image_id": image_id,
                "image_path": image_path,
                "face_bbox": bbox,
                "detection_confidence": detection_confidence,
                "embedding": embedding_norm.tolist(),
                "message": "Image validated successfully",
            }

        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error("Image validation failed: %s", e)
            raise ValueError(f"Image validation failed: {str(e)}")

    def get_cached_data(self, image_id: str) -> Optional[dict]:
        """
        Retrieve cached validation data for an image.

        Args:
            image_id: UUID of the validated image

        Returns:
            Cached data dict or None if not found/expired
        """
        cached = self._cache.get(image_id)
        if cached is None:
            return None

        # Check TTL
        if time.time() - cached["timestamp"] > config.VALIDATION_CACHE_TTL:
            del self._cache[image_id]
            return None

        return cached

    def cleanup_expired_entries(self):
        """Remove cache entries older than TTL."""
        now = time.time()
        expired = [
            k
            for k, v in self._cache.items()
            if now - v["timestamp"] > config.VALIDATION_CACHE_TTL
        ]
        for k in expired:
            del self._cache[k]
        if expired:
            logger.info("Cleaned up %d expired cache entries", len(expired))


# Global instance
image_validator = ImageValidator()
