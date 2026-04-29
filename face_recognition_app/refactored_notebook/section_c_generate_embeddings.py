"""
Face Recognition System - Section C: Generate ArcFace Embeddings (CSV → Database)
Phase 2: Notebook Refactoring

This section generates ArcFace embeddings from training images and saves them
directly to PostgreSQL instead of CSV files.
"""

import os
import sys
import logging
import numpy as np
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Import ML libraries
import cv2
from deepface import DeepFace
from database.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# CONFIGURATION
# ============================================================================

RECOGNITION_MODEL = os.getenv('RECOGNITION_MODEL', 'ArcFace')
DETECTOR_BACKEND = os.getenv('DETECTOR_BACKEND', 'mtcnn')
ALIGN_FACES = os.getenv('FACE_ALIGN', 'True').lower() == 'true'
TRAINING_DATA_DIR = os.getenv('TRAINING_DATA_DIR', './training_data')
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

# ============================================================================
# SECTION C: GENERATE ARCFACE EMBEDDINGS → DATABASE
# ============================================================================

def generate_and_save_embeddings(db: DatabaseConnection, training_dir: str):
    """
    Generate ArcFace embeddings from training data and save to database.
    
    Parameters
    ----------
    db : DatabaseConnection
        Database connection pool
    training_dir : str
        Root directory containing person subfolders with images
    """
    logger.info("=" * 70)
    logger.info("SECTION C: GENERATE ARCFACE EMBEDDINGS → DATABASE")
    logger.info("=" * 70)
    
    training_path = Path(training_dir)
    
    # Validate directory
    if not training_path.exists():
        logger.error(f"❌ Training directory not found: {training_dir}")
        logger.info("Create directory structure:")
        logger.info(f"  {training_dir}/")
        logger.info(f"    Person1/")
        logger.info(f"      image1.jpg")
        logger.info(f"      image2.jpg")
        return 0
    
    # Find person subdirectories
    person_dirs = sorted([
        p for p in training_path.iterdir()
        if p.is_dir() and not p.name.startswith('.')
    ])
    
    if not person_dirs:
        logger.warning(f"⚠️  No person subdirectories found in {training_dir}")
        return 0
    
    logger.info(f"Configuration:")
    logger.info(f"  Embedding model  : {RECOGNITION_MODEL}")
    logger.info(f"  Detector backend : {DETECTOR_BACKEND}")
    logger.info(f"  Face alignment   : {ALIGN_FACES}")
    logger.info(f"  Training persons : {[p.name for p in person_dirs]}")
    logger.info(f"\n")
    
    total_embedded = 0
    embeddings_summary = {}
    
    # Process each person's folder
    for person_dir in tqdm(person_dirs, desc="Processing persons"):
        person_name = person_dir.name
        
        # Get image files
        image_files = sorted([
            f for f in person_dir.iterdir()
            if f.suffix.lower() in IMAGE_EXTS
        ])
        
        if not image_files:
            logger.warning(f"  ⚠️  No images found in {person_name}/")
            continue
        
        logger.info(f"\n  Processing {person_name} ({len(image_files)} images)...")
        
        # Get or create person in database
        person_id = db.get_or_create_person(person_name)
        
        embeddings_list = []
        successful_count = 0
        
        # Generate embeddings for each image
        for img_file in tqdm(image_files, desc=f"    {person_name}", leave=False):
            try:
                # Generate embedding using DeepFace + ArcFace
                face_objs = DeepFace.represent(
                    img_path=str(img_file),
                    model_name=RECOGNITION_MODEL,
                    detector_backend=DETECTOR_BACKEND,
                    enforce_detection=True,
                    align=ALIGN_FACES,
                )
                
                if not face_objs:
                    logger.debug(f"    ✗ No face detected: {img_file.name}")
                    continue
                
                # If multiple faces, select the largest one
                face_objs.sort(
                    key=lambda x: x["facial_area"]["w"] * x["facial_area"]["h"],
                    reverse=True
                )
                best_face = face_objs[0]
                
                # Extract embedding and confidence
                embedding = np.array(best_face["embedding"], dtype=np.float32)
                confidence = best_face.get("face_confidence", 1.0)
                
                # Prepare for database insert
                embeddings_list.append({
                    'image_path': str(img_file.resolve()),
                    'embedding': embedding,
                    'face_confidence': float(confidence),
                    'source_type': 'training'
                })
                
                successful_count += 1
            
            except Exception as e:
                logger.debug(f"    ✗ Error processing {img_file.name}: {e}")
                continue
        
        # Save all embeddings for this person to database
        if embeddings_list:
            inserted = db.save_embeddings_batch(person_id, embeddings_list)
            embeddings_summary[person_name] = {
                'person_id': person_id,
                'images_attempted': len(image_files),
                'embeddings_saved': inserted
            }
            total_embedded += inserted
            logger.info(f"  ✅ {person_name}: {inserted}/{len(image_files)} embeddings saved")
        else:
            logger.warning(f"  ⚠️  {person_name}: No valid embeddings generated")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SECTION C SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total embeddings generated and saved: {total_embedded}")
    logger.info(f"Persons processed: {len(embeddings_summary)}")
    
    for person_name, stats in embeddings_summary.items():
        logger.info(f"  {person_name:20s} {stats['embeddings_saved']:3d} embeddings")
    
    # Verify in database
    face_counts = db.get_face_count_by_person()
    logger.info(f"\nVerification (from database):")
    for person, count in sorted(face_counts.items()):
        logger.info(f"  {person:20s} {count:3d} faces")
    
    return total_embedded


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        # Initialize database
        from section_a_db_init import initialize_database
        db = initialize_database()
        
        # Generate embeddings
        total = generate_and_save_embeddings(db, TRAINING_DATA_DIR)
        
        if total > 0:
            logger.info(f"\n✅ SUCCESS: {total} embeddings saved to database")
            logger.info("Next: Run section_d_train_svm.py to train the SVM classifier")
        else:
            logger.error("❌ No embeddings generated. Check training_data folder.")
    
    except Exception as e:
        logger.error(f"❌ Error in Section C: {e}", exc_info=True)
        sys.exit(1)
