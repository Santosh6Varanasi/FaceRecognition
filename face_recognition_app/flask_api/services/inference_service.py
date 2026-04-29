"""
Inference service — run face detection + SVM identification on a single frame.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import time
from typing import Optional

import numpy as np
from deepface import DeepFace
from sklearn.preprocessing import normalize

import model_cache
from config import config
from db import queries
from services import image_service

logger = logging.getLogger(__name__)


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector (normalized)
        embedding2: Second embedding vector (normalized)
    
    Returns:
        Cosine similarity value between -1 and 1 (typically 0 to 1 for normalized vectors)
    """
    return float(np.dot(embedding1, embedding2))


def is_duplicate_face(embedding: np.ndarray, db, similarity_threshold: float = 0.6) -> bool:
    """
    Check if a face embedding is a duplicate of an existing unknown face.
    
    Compares the given embedding with all existing unknown faces in the database.
    Returns True if any existing face has cosine similarity > threshold.
    
    Args:
        embedding: Face embedding vector (normalized)
        db: Database connection
        similarity_threshold: Minimum similarity to consider faces as duplicates (default 0.6)
    
    Returns:
        True if face is a duplicate, False otherwise
    
    Requirements: 8.5
    """
    try:
        # Get all existing unknown face embeddings
        existing_faces = queries.get_all_unknown_face_embeddings(db)
        
        # Compare with each existing face
        for face in existing_faces:
            existing_embedding = np.array(face["embedding"], dtype=np.float64)
            similarity = cosine_similarity(embedding, existing_embedding)
            
            if similarity > similarity_threshold:
                logger.info(
                    "Duplicate face detected: similarity=%.3f with face_id=%d (threshold=%.2f)",
                    similarity, face["id"], similarity_threshold
                )
                return True
        
        return False
    except Exception as exc:
        logger.warning("Error checking for duplicate faces: %s", exc)
        # On error, allow the face to be stored (fail open)
        return False


def run_inference(frame_bgr: np.ndarray, session_id: str, db, timestamp_ms: int = 0, video_id: Optional[int] = None, frame_number: int = 0) -> dict:
    t_start = time.time()

    # 1. Try to load active model — OK if none exists yet
    model_available = False
    svm = None
    label_encoder = None
    try:
        svm, label_encoder = model_cache.get_active_model(db)
        model_available = True
    except Exception as exc:
        logger.info("No model loaded (%s) — will label all faces as Unknown.", exc)

    # 2. Detect faces — try configured backend, fall back to opencv
    face_objs = []
    backends_to_try = [config.DETECTOR_BACKEND, "opencv", "ssd"]
    for backend in backends_to_try:
        try:
            face_objs = DeepFace.extract_faces(
                img_path=frame_bgr,
                detector_backend=backend,
                enforce_detection=False,
                align=True,
            )
            # Filter out low-confidence detections (DeepFace returns conf=0 for "no face")
            face_objs = [f for f in face_objs if f.get("confidence", 0) > 0.5 or backend == "opencv"]
            if face_objs:
                logger.info("Detected %d face(s) using backend '%s'", len(face_objs), backend)
                break
            else:
                logger.info("Backend '%s' found no faces, trying next...", backend)
        except Exception as exc:
            logger.warning("Backend '%s' failed: %s", backend, exc)
            face_objs = []

    logger.info("Total face_objs after detection: %d", len(face_objs))

    detections = []

    for face_obj in face_objs:
        try:
            face_img = face_obj.get("face")
            if face_img is None:
                logger.warning("face_obj has no 'face' key, skipping")
                continue

            # Build bbox
            area = face_obj.get("facial_area", {})
            bbox = {
                "x1": int(area.get("x", 0)),
                "y1": int(area.get("y", 0)),
                "x2": int(area.get("x", 0) + area.get("w", 0)),
                "y2": int(area.get("y", 0) + area.get("h", 0)),
            }
            det_conf = float(face_obj.get("confidence", 1.0))
            logger.info("Face bbox=%s conf=%.2f", bbox, det_conf)

            # Skip tiny/invalid boxes
            if bbox["x2"] - bbox["x1"] < 10 or bbox["y2"] - bbox["y1"] < 10:
                logger.warning("Skipping tiny bbox: %s", bbox)
                continue

            unknown_face_id: Optional[int] = None
            person_id: Optional[int] = None
            name = "Unknown"
            top_prob = 0.0

            if model_available:
                # Convert to uint8 BGR
                if face_img.dtype != np.uint8:
                    face_img_bgr = (face_img[:, :, ::-1] * 255).astype(np.uint8)
                else:
                    face_img_bgr = face_img[:, :, ::-1]

                # Generate ArcFace embedding
                repr_objs = DeepFace.represent(
                    img_path=face_img_bgr,
                    model_name=config.RECOGNITION_MODEL,
                    detector_backend="skip",
                    enforce_detection=False,
                )
                if repr_objs:
                    embedding = np.array(repr_objs[0]["embedding"], dtype=np.float64)
                    embedding_norm = normalize(embedding.reshape(1, -1), norm="l2")[0]

                    proba = svm.predict_proba([embedding_norm])[0]
                    top_idx = int(np.argmax(proba))
                    top_prob = float(proba[top_idx])

                    if top_prob < config.SVM_CONFIDENCE_THRESHOLD:
                        name = "Unknown"
                        # Calculate frame timestamp in seconds for unknown face storage
                        frame_timestamp_sec = timestamp_ms / 1000.0 if timestamp_ms else 0.0
                        
                        # Check for duplicate faces before storing (Requirement 8.5)
                        if not is_duplicate_face(embedding_norm, db, similarity_threshold=0.6):
                            # Save unknown face with video source tracking
                            unknown_face_id = queries.insert_unknown_face(
                                conn=db,
                                embedding=embedding_norm,
                                source_image_path="",
                                frame_id=None,
                                detection_confidence=det_conf,
                                svm_prediction=name,
                                svm_probability=top_prob,
                                source_video_id=video_id,
                                frame_timestamp=frame_timestamp_sec,
                                frame_number=frame_number,
                            )
                            image_service.crop_and_save_face(frame_bgr, bbox, unknown_face_id)
                        else:
                            logger.info("Skipping duplicate unknown face (similarity > 0.6)")
                    else:
                        name = str(label_encoder.inverse_transform([top_idx])[0])
                        raw_conn = db.get_connection()
                        try:
                            cursor = raw_conn.cursor()
                            cursor.execute("SELECT id FROM people WHERE name = %s LIMIT 1", (name,))
                            row = cursor.fetchone()
                            person_id = row[0] if row else None
                            cursor.close()
                        finally:
                            db.return_connection(raw_conn)
            else:
                # No model — save as unknown so user can label later
                try:
                    if face_img.dtype != np.uint8:
                        face_img_bgr = (face_img[:, :, ::-1] * 255).astype(np.uint8)
                    else:
                        face_img_bgr = face_img[:, :, ::-1]
                    repr_objs = DeepFace.represent(
                        img_path=face_img_bgr,
                        model_name=config.RECOGNITION_MODEL,
                        detector_backend="skip",
                        enforce_detection=False,
                    )
                    if repr_objs:
                        embedding_norm = normalize(
                            np.array(repr_objs[0]["embedding"], dtype=np.float64).reshape(1, -1),
                            norm="l2"
                        )[0]
                        # Calculate frame timestamp in seconds for unknown face storage
                        frame_timestamp_sec = timestamp_ms / 1000.0 if timestamp_ms else 0.0
                        
                        # Check for duplicate faces before storing (Requirement 8.5)
                        if not is_duplicate_face(embedding_norm, db, similarity_threshold=0.6):
                            # Save unknown face with video source tracking
                            unknown_face_id = queries.insert_unknown_face(
                                conn=db,
                                embedding=embedding_norm,
                                source_image_path="",
                                frame_id=None,
                                detection_confidence=det_conf,
                                svm_prediction="Unknown",
                                svm_probability=0.0,
                                source_video_id=video_id,
                                frame_timestamp=frame_timestamp_sec,
                                frame_number=frame_number,
                            )
                            image_service.crop_and_save_face(frame_bgr, bbox, unknown_face_id)
                        else:
                            logger.info("Skipping duplicate unknown face (similarity > 0.6)")
                except Exception as emb_exc:
                    logger.warning("Embedding failed (no model path): %s", emb_exc)

            detections.append({
                "bbox": bbox,
                "name": name,
                "confidence": top_prob,
                "detection_confidence": det_conf,
                "person_id": person_id,
                "unknown_face_id": unknown_face_id,
                "embedding": None,
            })

        except Exception as exc:
            logger.warning("Error processing face: %s", exc)
            continue

    # 3. Insert frame
    h, w = frame_bgr.shape[:2]
    frame_id: Optional[int] = None
    try:
        frame_id = queries.insert_frame(
            conn=db, session_id=session_id, frame_number=0, width=w, height=h,
            timestamp_ms=timestamp_ms,
        )
    except Exception as exc:
        logger.warning("Failed to insert frame: %s", exc)

    # 4. Insert detections
    for det in detections:
        try:
            queries.insert_detection(
                conn=db,
                frame_id=frame_id,
                person_id=det["person_id"],
                unknown_face_id=det["unknown_face_id"],
                bbox_x1=det["bbox"]["x1"],
                bbox_y1=det["bbox"]["y1"],
                bbox_x2=det["bbox"]["x2"],
                bbox_y2=det["bbox"]["y2"],
                svm_prediction=det["name"],
                svm_probability=det["confidence"],
                detection_confidence=det["detection_confidence"],
            )
        except Exception as exc:
            logger.warning("Failed to insert detection: %s", exc)
    
    # 5. Insert video detections if video_id is provided
    if video_id is not None:
        timestamp_sec = timestamp_ms / 1000.0 if timestamp_ms else 0.0
        for det in detections:
            try:
                is_unknown = det["confidence"] < config.SVM_CONFIDENCE_THRESHOLD
                queries.insert_video_detection(
                    conn=db,
                    video_id=video_id,
                    frame_number=frame_number,
                    timestamp=timestamp_sec,
                    person_id=det["person_id"],
                    person_name=det["name"],
                    bbox_x1=det["bbox"]["x1"],
                    bbox_y1=det["bbox"]["y1"],
                    bbox_x2=det["bbox"]["x2"],
                    bbox_y2=det["bbox"]["y2"],
                    recognition_confidence=det["confidence"],
                    detection_confidence=det["detection_confidence"],
                    is_unknown=is_unknown,
                )
            except Exception as exc:
                logger.warning("Failed to insert video detection: %s", exc)

    elapsed_ms = (time.time() - t_start) * 1000
    logger.info("Returning %d detections in %.0fms", len(detections), elapsed_ms)

    return {
        "detections": [
            {
                "bbox": d["bbox"],
                "name": d["name"],
                "confidence": d["confidence"],
                "detection_confidence": d["detection_confidence"],
            }
            for d in detections
        ],
        "frame_id": frame_id,
        "processing_time_ms": round(elapsed_ms, 2),
    }
