#!/usr/bin/env python3
"""
============================================================================
STANDALONE MODEL TRAINING SCRIPT (DeepFace + ArcFace)
============================================================================
Purpose: Train face recognition model from training_data folder
Usage: python train_model_standalone.py
Requirements: training_data/ folder with subfolders for each person
Technology: DeepFace with ArcFace embeddings + SVM classifier
============================================================================
"""

import os
import sys
import io
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, normalize
from deepface import DeepFace
import joblib
import cv2

# ============================================================================
# CONFIGURATION
# ============================================================================
TRAINING_DATA_DIR = "training_data/training_data"
MODEL_OUTPUT_DIR = "face_recognition_app/models"
MODEL_FILENAME = "svm_model.pkl"
LABEL_ENCODER_FILENAME = "label_encoder.pkl"
METADATA_FILENAME = "model_metadata.pkl"

# DeepFace Configuration (matching existing implementation)
RECOGNITION_MODEL = "ArcFace"  # Same as config.py
DETECTOR_BACKEND = "mtcnn"     # Same as config.py

# SVM Parameters (matching model_retrainer.py)
SVM_KERNEL = 'rbf'
SVM_GAMMA = 'scale'
SVM_C = 10  # Changed from 1.0 to 10 to match model_retrainer.py
CV_FOLDS = 5

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_step(step_num, text):
    """Print formatted step"""
    print(f"\n[Step {step_num}] {text}")

def print_success(text):
    """Print success message"""
    print(f"✓ {text}")

def print_error(text):
    """Print error message"""
    print(f"✗ ERROR: {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠ WARNING: {text}")

# ============================================================================
# MAIN TRAINING FUNCTIONS
# ============================================================================

def validate_training_data():
    """Validate training data directory structure"""
    print_step(1, "Validating training data directory")
    
    if not os.path.exists(TRAINING_DATA_DIR):
        print_error(f"Training data directory not found: {TRAINING_DATA_DIR}")
        print(f"\nPlease create the directory structure:")
        print(f"  {TRAINING_DATA_DIR}/")
        print(f"    ├── person1/")
        print(f"    │   ├── image1.jpg")
        print(f"    │   └── image2.jpg")
        print(f"    ├── person2/")
        print(f"    │   ├── image1.jpg")
        print(f"    │   └── image2.jpg")
        print(f"    └── ...")
        return False
    
    # Get person directories
    person_dirs = [d for d in os.listdir(TRAINING_DATA_DIR) 
                   if os.path.isdir(os.path.join(TRAINING_DATA_DIR, d))]
    
    if len(person_dirs) == 0:
        print_error("No person directories found in training_data/")
        print("Please create subdirectories for each person with their photos")
        return False
    
    print_success(f"Found {len(person_dirs)} person directories")
    
    # Validate each person has images
    total_images = 0
    for person_name in person_dirs:
        person_path = os.path.join(TRAINING_DATA_DIR, person_name)
        images = [f for f in os.listdir(person_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if len(images) == 0:
            print_warning(f"No images found for {person_name}")
        else:
            print(f"  - {person_name}: {len(images)} images")
            total_images += len(images)
    
    if total_images == 0:
        print_error("No training images found")
        return False
    
    print_success(f"Total training images: {total_images}")
    return True

def load_training_data():
    """Load and encode all training images using DeepFace + ArcFace"""
    print_step(2, "Loading and encoding training images with DeepFace + ArcFace")
    
    embeddings = []
    labels = []
    failed_images = []
    
    person_dirs = [d for d in os.listdir(TRAINING_DATA_DIR) 
                   if os.path.isdir(os.path.join(TRAINING_DATA_DIR, d))]
    
    for person_name in person_dirs:
        person_path = os.path.join(TRAINING_DATA_DIR, person_name)
        image_files = [f for f in os.listdir(person_path) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
        print(f"\n  Processing {person_name}...")
        
        for image_file in image_files:
            image_path = os.path.join(person_path, image_file)
            
            try:
                # Load image with OpenCV
                image_bgr = cv2.imread(image_path)
                
                if image_bgr is None:
                    print_error(f"Failed to load {image_file}")
                    failed_images.append((person_name, image_file, "Failed to load image"))
                    continue
                
                # Extract faces using DeepFace
                face_objs = DeepFace.extract_faces(
                    img_path=image_bgr,
                    detector_backend=DETECTOR_BACKEND,
                    enforce_detection=False,
                    align=True,
                )
                
                # Filter out low-confidence detections
                face_objs = [f for f in face_objs if f.get("confidence", 0) > 0.5]
                
                if len(face_objs) == 0:
                    print_warning(f"No face detected in {image_file}")
                    failed_images.append((person_name, image_file, "No face detected"))
                    continue
                
                if len(face_objs) > 1:
                    print_warning(f"Multiple faces detected in {image_file}, using first face")
                
                # Get the first face
                face_img = face_objs[0].get("face")
                if face_img is None:
                    print_warning(f"No face data in {image_file}")
                    failed_images.append((person_name, image_file, "No face data"))
                    continue
                
                # Convert to uint8 BGR for DeepFace.represent
                if face_img.dtype != np.uint8:
                    face_img_bgr = (face_img[:, :, ::-1] * 255).astype(np.uint8)
                else:
                    face_img_bgr = face_img[:, :, ::-1]
                
                # Generate ArcFace embedding (matching inference_service.py)
                repr_objs = DeepFace.represent(
                    img_path=face_img_bgr,
                    model_name=RECOGNITION_MODEL,
                    detector_backend="skip",  # Skip detection since we already extracted face
                    enforce_detection=False,
                )
                
                if not repr_objs:
                    print_warning(f"Failed to generate embedding for {image_file}")
                    failed_images.append((person_name, image_file, "Failed to generate embedding"))
                    continue
                
                # Get embedding and normalize (matching model_retrainer.py)
                embedding = np.array(repr_objs[0]["embedding"], dtype=np.float64)
                embedding_norm = normalize(embedding.reshape(1, -1), norm="l2")[0]
                
                embeddings.append(embedding_norm)
                labels.append(person_name)
                print(f"    ✓ {image_file}")
                
            except Exception as e:
                print_error(f"Failed to process {image_file}: {str(e)}")
                failed_images.append((person_name, image_file, str(e)))
    
    if len(embeddings) == 0:
        print_error("No valid face embeddings extracted")
        return None, None, failed_images
    
    print_success(f"Successfully encoded {len(embeddings)} faces")
    
    if failed_images:
        print_warning(f"Failed to process {len(failed_images)} images")
    
    return np.array(embeddings), np.array(labels), failed_images

def train_model(embeddings, labels):
    """Train SVM classifier with cross-validation (matching model_retrainer.py)"""
    print_step(3, "Training SVM classifier")
    
    # Encode labels
    label_encoder = LabelEncoder()
    encoded_labels = label_encoder.fit_transform(labels)
    
    num_classes = len(label_encoder.classes_)
    num_samples = len(embeddings)
    
    print(f"  - Number of classes: {num_classes}")
    print(f"  - Number of training samples: {num_samples}")
    print(f"  - Classes: {', '.join(label_encoder.classes_)}")
    
    # Check minimum samples per class
    unique, counts = np.unique(labels, return_counts=True)
    min_samples = min(counts)
    
    print(f"\n  Samples per class:")
    for name, count in zip(unique, counts):
        print(f"    - {name}: {count} samples")
    
    if min_samples < 2:
        print_warning(f"Some classes have less than 2 samples. Cross-validation may fail.")
        print("  Consider adding more images for each person.")
    
    # Train SVM (matching model_retrainer.py parameters)
    print(f"\n  Training SVM (kernel={SVM_KERNEL}, C={SVM_C}, gamma={SVM_GAMMA})...")
    svm_model = SVC(kernel=SVM_KERNEL, C=SVM_C, gamma=SVM_GAMMA, probability=True)
    
    # Cross-validation before final training
    print(f"\n  Performing {CV_FOLDS}-fold cross-validation...")
    try:
        cv_folds = min(CV_FOLDS, min_samples)  # Adjust folds if needed
        if cv_folds < CV_FOLDS:
            print_warning(f"Reduced CV folds to {cv_folds} due to limited samples")
        
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        cv_scores = cross_val_score(
            svm_model, 
            embeddings, 
            encoded_labels, 
            cv=cv,
            scoring="accuracy"
        )
        
        cv_accuracy = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
        
        print_success(f"Cross-validation accuracy: {cv_accuracy:.2%} (+/- {cv_std:.2%})")
        
        # Print per-fold scores
        for i, score in enumerate(cv_scores, 1):
            print(f"    Fold {i}: {score:.2%}")
        
    except Exception as e:
        print_warning(f"Cross-validation failed: {str(e)}")
        cv_accuracy = None
        cv_std = None
    
    # Fit the final model on all data (matching model_retrainer.py)
    print(f"\n  Training final model on all data...")
    svm_model.fit(embeddings, encoded_labels)
    print_success("Model trained successfully")
    
    return svm_model, label_encoder, cv_accuracy, cv_std, num_classes, num_samples

def save_model(svm_model, label_encoder, cv_accuracy, cv_std, num_classes, num_samples):
    """Save trained model and metadata (matching model_retrainer.py format)"""
    print_step(4, "Saving model")
    
    # Create output directory
    os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
    
    # Save SVM model using joblib (matching model_retrainer.py)
    model_path = os.path.join(MODEL_OUTPUT_DIR, MODEL_FILENAME)
    model_buf = io.BytesIO()
    joblib.dump(svm_model, model_buf)
    model_bytes = model_buf.getvalue()
    
    with open(model_path, 'wb') as f:
        f.write(model_bytes)
    print_success(f"Model saved to {model_path}")
    
    # Save label encoder using joblib (matching model_retrainer.py)
    encoder_path = os.path.join(MODEL_OUTPUT_DIR, LABEL_ENCODER_FILENAME)
    le_buf = io.BytesIO()
    joblib.dump(label_encoder, le_buf)
    le_bytes = le_buf.getvalue()
    
    with open(encoder_path, 'wb') as f:
        f.write(le_bytes)
    print_success(f"Label encoder saved to {encoder_path}")
    
    # Save metadata
    metadata = {
        'num_classes': num_classes,
        'num_training_samples': num_samples,
        'cross_validation_accuracy': cv_accuracy,
        'cross_validation_std': cv_std,
        'classes': label_encoder.classes_.tolist(),
        'trained_at': datetime.now().isoformat(),
        'recognition_model': RECOGNITION_MODEL,
        'detector_backend': DETECTOR_BACKEND,
        'svm_kernel': SVM_KERNEL,
        'svm_c': SVM_C,
        'svm_gamma': SVM_GAMMA
    }
    
    metadata_path = os.path.join(MODEL_OUTPUT_DIR, METADATA_FILENAME)
    with open(metadata_path, 'wb') as f:
        joblib.dump(metadata, f)
    print_success(f"Metadata saved to {metadata_path}")
    
    return metadata

def print_summary(metadata, failed_images):
    """Print training summary"""
    print_header("TRAINING SUMMARY")
    
    print(f"\n✓ Model trained successfully!")
    print(f"\n  Model Details:")
    print(f"    - Recognition Model: {metadata['recognition_model']}")
    print(f"    - Detector Backend: {metadata['detector_backend']}")
    print(f"    - Classes: {metadata['num_classes']}")
    print(f"    - Training samples: {metadata['num_training_samples']}")
    if metadata['cross_validation_accuracy']:
        print(f"    - CV Accuracy: {metadata['cross_validation_accuracy']:.2%} (+/- {metadata['cross_validation_std']:.2%})")
    print(f"    - SVM Kernel: {metadata['svm_kernel']}")
    print(f"    - SVM C: {metadata['svm_c']}")
    print(f"    - Trained at: {metadata['trained_at']}")
    
    print(f"\n  Recognized People:")
    for i, person in enumerate(metadata['classes'], 1):
        print(f"    {i}. {person}")
    
    if failed_images:
        print(f"\n  ⚠ Failed Images ({len(failed_images)}):")
        for person, image, reason in failed_images[:10]:  # Show first 10
            print(f"    - {person}/{image}: {reason}")
        if len(failed_images) > 10:
            print(f"    ... and {len(failed_images) - 10} more")
    
    print(f"\n  Model Files:")
    print(f"    - {os.path.join(MODEL_OUTPUT_DIR, MODEL_FILENAME)}")
    print(f"    - {os.path.join(MODEL_OUTPUT_DIR, LABEL_ENCODER_FILENAME)}")
    print(f"    - {os.path.join(MODEL_OUTPUT_DIR, METADATA_FILENAME)}")
    
    print("\n" + "=" * 80)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main training pipeline"""
    print_header("FACE RECOGNITION MODEL TRAINING (DeepFace + ArcFace)")
    print(f"Training data directory: {TRAINING_DATA_DIR}")
    print(f"Model output directory: {MODEL_OUTPUT_DIR}")
    print(f"Recognition model: {RECOGNITION_MODEL}")
    print(f"Detector backend: {DETECTOR_BACKEND}")
    
    try:
        # Step 1: Validate training data
        if not validate_training_data():
            sys.exit(1)
        
        # Step 2: Load and encode training images
        embeddings, labels, failed_images = load_training_data()
        if embeddings is None:
            sys.exit(1)
        
        # Step 3: Train model
        svm_model, label_encoder, cv_accuracy, cv_std, num_classes, num_samples = train_model(
            embeddings, labels
        )
        
        # Step 4: Save model
        metadata = save_model(svm_model, label_encoder, cv_accuracy, cv_std, num_classes, num_samples)
        
        # Print summary
        print_summary(metadata, failed_images)
        
        print("\n✓ Training completed successfully!")
        print("\nNext steps:")
        print("  1. Start the Flask API server")
        print("  2. The new model will be loaded automatically")
        print("  3. Test face recognition with your images/videos")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Training interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Training failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
