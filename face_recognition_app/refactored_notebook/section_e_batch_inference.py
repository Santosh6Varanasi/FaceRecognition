"""
Face Recognition System - Section E: Batch Inference with Frame & Detection Tracking
Phase 2: Notebook Refactoring

This section processes test images, detects faces, identifies persons,
and persists results (frames, detections, unknown_faces) to database.
"""

import os
import sys
import logging
import numpy as np
import uuid
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

import cv2
from deepface import DeepFace
from sklearn.preprocessing import normalize
from database.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# CONFIGURATION
# ============================================================================

RECOGNITION_MODEL = os.getenv('RECOGNITION_MODEL', 'ArcFace')
DETECTOR_BACKEND = os.getenv('DETECTOR_BACKEND', 'mtcnn')
ALIGN_FACES = os.getenv('FACE_ALIGN', 'True').lower() == 'true'
SVM_CONFIDENCE_THRESHOLD = float(os.getenv('SVM_CONFIDENCE_THRESHOLD', 0.50))
TEST_IMAGES_DIR = os.getenv('TEST_IMAGES_DIR', './test_images')
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

# ============================================================================
# FACE RECOGNITION HELPER CLASS
# ============================================================================

class FaceRecognizer:
    """Wrapper for SVM-based face identification."""
    
    def __init__(self, svm_model, label_encoder, threshold: float = 0.50):
        self.model = svm_model
        self.le = label_encoder
        self.threshold = threshold
        self.known_names = list(self.le.classes_)
    
    def identify(self, embedding: np.ndarray) -> Tuple[str, float]:
        """
        Identify a face embedding.
        
        Returns
        -------
        Tuple[name, probability]
            name: person name if confident, else 'Unknown'
            probability: SVM top-class probability (0-1)
        """
        # L2-normalize
        vec = normalize(
            np.array(embedding, dtype=np.float64).reshape(1, -1),
            norm='l2'
        )
        
        # Get SVM probabilities
        proba = self.model.predict_proba(vec)[0]
        best_idx = int(np.argmax(proba))
        best_prob = float(proba[best_idx])
        
        # Threshold check
        if best_prob >= self.threshold:
            name = str(self.le.inverse_transform([best_idx])[0])
            return name, best_prob
        
        return "Unknown", best_prob


# ============================================================================
# SECTION E: BATCH INFERENCE WITH FRAME & DETECTION TRACKING
# ============================================================================

def run_batch_inference(db: DatabaseConnection, test_dir: str):
    """
    Process all test images, detect faces, identify persons,
    and save results to database.
    
    Parameters
    ----------
    db : DatabaseConnection
        Database connection
    test_dir : str
        Root directory with test images
    """
    logger.info("=" * 70)
    logger.info("SECTION E: BATCH INFERENCE WITH FRAME & DETECTION TRACKING")
    logger.info("=" * 70)
    
    # Load active model
    logger.info("\nLoading active SVM model from database...")
    try:
        svm, le = db.load_active_model()
        recognizer = FaceRecognizer(svm, le, threshold=SVM_CONFIDENCE_THRESHOLD)
        logger.info(f"✅ Loaded model with {len(recognizer.known_names)} persons")
        logger.info(f"   Known persons: {recognizer.known_names}")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        logger.info("Train a model first using section_d_train_svm.py")
        return
    
    # Create video session
    logger.info("\nCreating video session...")
    session_id = db.create_video_session(
        session_name="batch_inference",
        camera_source="test_images",
        notes=f"Batch inference on {test_dir}"
    )
    logger.info(f"✅ Created session: {session_id}")
    
    # Find test images
    test_path = Path(test_dir)
    if not test_path.exists():
        logger.error(f"❌ Test directory not found: {test_dir}")
        return
    
    # Collect all test images
    test_images: List[Tuple[str, str]] = []  # (ground_truth, image_path)
    person_dirs = sorted([p for p in test_path.iterdir() if p.is_dir()])
    
    for person_dir in person_dirs:
        person_name = person_dir.name
        images = sorted([f for f in person_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS])
        for img in images:
            test_images.append((person_name, str(img)))
    
    if not test_images:
        logger.warning(f"⚠️  No test images found in {test_dir}")
        return
    
    logger.info(f"Found {len(test_images)} test images")
    
    # Process each image
    frame_results = {
        'total_frames': 0,
        'total_detections': 0,
        'correct_identifications': 0,
        'unknown_faces': 0,
        'per_person': {}
    }
    
    frame_number = 0
    
    for ground_truth, image_path in tqdm(test_images, desc="Processing images"):
        frame_number += 1
        
        try:
            # Insert frame metadata
            frame_id = db.insert_frame(
                session_id=session_id,
                frame_number=frame_number,
                image_path=image_path,
                width=1920,  # Will update from actual image
                height=1080
            )
            
            frame_results['total_frames'] += 1
            
            # Detect and embed faces
            face_objs = DeepFace.represent(
                img_path=image_path,
                model_name=RECOGNITION_MODEL,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=False,
                align=ALIGN_FACES
            )
            
            if not face_objs:
                logger.debug(f"  No faces detected in {Path(image_path).name}")
                continue
            
            # Get image dimensions
            img = cv2.imread(image_path)
            if img is not None:
                h, w = img.shape[:2]
                # Update frame dimensions
                db_conn = db.get_connection()
                cursor = db_conn.cursor()
                cursor.execute(
                    "UPDATE frames SET width=%s, height=%s WHERE id=%s",
                    (w, h, frame_id)
                )
                db_conn.commit()
                cursor.close()
                db.return_connection(db_conn)
            
            # Process each detected face
            for face_obj in face_objs:
                embedding = np.array(face_obj['embedding'], dtype=np.float32)
                area = face_obj['facial_area']
                det_conf = face_obj.get('face_confidence', 1.0)
                
                # Identify
                name, prob = recognizer.identify(embedding)
                
                frame_results['total_detections'] += 1
                
                # Prepare detection record
                bbox = {
                    'x1': int(area['x']),
                    'y1': int(area['y']),
                    'x2': int(area['x'] + area['w']),
                    'y2': int(area['y'] + area['h'])
                }
                
                if name != "Unknown":
                    # Known person
                    person_id = None
                    for p in db.get_all_people():
                        if p['name'] == name:
                            person_id = p['id']
                            break
                    
                    is_correct = (name == ground_truth)
                    frame_results['correct_identifications'] += is_correct
                    
                    db.insert_detection(
                        frame_id=frame_id,
                        embedding=embedding,
                        svm_prediction=name,
                        svm_probability=prob,
                        detection_confidence=det_conf,
                        bbox=bbox,
                        person_id=person_id,
                        unknown_face_id=None
                    )
                    
                    # Track per-person stats
                    if ground_truth not in frame_results['per_person']:
                        frame_results['per_person'][ground_truth] = {
                            'total': 0, 'correct': 0
                        }
                    frame_results['per_person'][ground_truth]['total'] += 1
                    if is_correct:
                        frame_results['per_person'][ground_truth]['correct'] += 1
                
                else:
                    # Unknown person
                    frame_results['unknown_faces'] += 1
                    
                    # Save to unknown_faces table
                    unknown_id = db.save_unknown_face(
                        embedding=embedding,
                        source_image_path=image_path,
                        source_frame_id=frame_id,
                        detection_confidence=det_conf,
                        svm_prediction=name,
                        svm_probability=prob
                    )
                    
                    # Insert detection linked to unknown
                    db.insert_detection(
                        frame_id=frame_id,
                        embedding=embedding,
                        svm_prediction=name,
                        svm_probability=prob,
                        detection_confidence=det_conf,
                        bbox=bbox,
                        person_id=None,
                        unknown_face_id=unknown_id
                    )
        
        except Exception as e:
            logger.warning(f"⚠️  Error processing {image_path}: {e}")
            continue
    
    # Update session stats
    db_conn = db.get_connection()
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE video_sessions SET total_frames=%s, end_time=NOW() WHERE id=%s",
        (frame_number, session_id)
    )
    db_conn.commit()
    cursor.close()
    db.return_connection(db_conn)
    
    # Report results
    logger.info("\n" + "=" * 70)
    logger.info("SECTION E SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Frames processed     : {frame_results['total_frames']}")
    logger.info(f"Faces detected       : {frame_results['total_detections']}")
    logger.info(f"Correctly identified : {frame_results['correct_identifications']}")
    logger.info(f"Unknown faces        : {frame_results['unknown_faces']}")
    
    if frame_results['total_detections'] > 0:
        accuracy = frame_results['correct_identifications'] / frame_results['total_detections'] * 100
        logger.info(f"Overall accuracy     : {accuracy:.1f}%")
    
    logger.info(f"\nPer-person breakdown:")
    for person, stats in sorted(frame_results['per_person'].items()):
        acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        logger.info(f"  {person:20s} {stats['correct']}/{stats['total']:2d}  ({acc:5.1f}%)")
    
    return frame_results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        from section_a_db_init import initialize_database
        db = initialize_database()
        
        # Run batch inference
        results = run_batch_inference(db, TEST_IMAGES_DIR)
        
        logger.info(f"\n✅ Batch inference complete")
        logger.info("Next: Run section_f_label_unknowns.py to label unknown faces")
    
    except Exception as e:
        logger.error(f"❌ Error in Section E: {e}", exc_info=True)
        sys.exit(1)
