"""
Face Recognition System - Section D: Train SVM from Database
Phase 2: Notebook Refactoring

This section trains an SVM classifier on embeddings loaded from PostgreSQL
and saves the model to the database with version tracking.
"""

import os
import sys
import logging
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from dotenv import load_dotenv
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Import ML libraries
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder, normalize
from sklearn.model_selection import StratifiedKFold, cross_val_score
from database.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# CONFIGURATION
# ============================================================================

SVM_C = float(os.getenv('SVM_C', 10.0))
SVM_GAMMA = os.getenv('SVM_GAMMA', 'scale')
CV_FOLDS = 5

# ============================================================================
# SECTION D: TRAIN SVM FROM DATABASE
# ============================================================================

def load_embeddings_for_training(db: DatabaseConnection, 
                                 include_unknown_labeled: bool = False) \
        -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Load embeddings from database for SVM training.
    
    Parameters
    ----------
    db : DatabaseConnection
        Database connection
    include_unknown_labeled : bool
        Whether to include labeled unknown faces in training
    
    Returns
    -------
    Tuple[X, y, label_names]
        - X: Embeddings array (N, 512)
        - y: Person name array (N,)
        - label_names: List of unique person names
    """
    logger.info("Loading embeddings from database...")
    
    embeddings, person_names = db.load_embeddings_for_training(
        include_unknown_labeled=include_unknown_labeled
    )
    
    if not embeddings:
        logger.error("❌ No embeddings found in database")
        raise ValueError("No embeddings available for training")
    
    X = np.array(embeddings, dtype=np.float64)
    y = np.array(person_names, dtype=object)
    
    unique_persons = sorted(list(set(person_names)))
    
    logger.info(f"✅ Loaded {len(embeddings)} embeddings")
    logger.info(f"   Persons: {unique_persons}")
    logger.info(f"   Embedding shape: {X.shape}")
    logger.info(f"   Unique persons: {len(unique_persons)}")
    
    # Check minimum samples per class
    unique, counts = np.unique(y, return_counts=True)
    min_samples = int(counts.min())
    logger.info(f"   Min samples per person: {min_samples}")
    
    return X, y, unique_persons


def normalize_embeddings(X: np.ndarray) -> np.ndarray:
    """
    L2-normalize embeddings for SVM training.
    
    Parameters
    ----------
    X : np.ndarray
        Unnormalized embeddings (N, 512)
    
    Returns
    -------
    np.ndarray
        L2-normalized embeddings (unit vectors)
    """
    logger.info("L2-normalizing embeddings...")
    X_norm = normalize(X, norm='l2')
    logger.info(f"✅ Normalized {len(X)} embeddings to unit vectors")
    return X_norm


def train_svm_with_cv(X_norm: np.ndarray, y: np.ndarray,
                      unique_persons: List[str]) -> Tuple[SVC, LabelEncoder, np.ndarray]:
    """
    Train SVM with stratified K-fold cross-validation.
    
    Parameters
    ----------
    X_norm : np.ndarray
        L2-normalized embeddings
    y : np.ndarray
        Person names
    unique_persons : List[str]
        List of unique person names
    
    Returns
    -------
    Tuple[svm_model, label_encoder, cv_scores]
    """
    logger.info("\nEncoding labels...")
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    
    label_mapping = dict(zip(le.classes_, le.transform(le.classes_)))
    logger.info(f"✅ Label encoding: {label_mapping}")
    
    logger.info("\nTraining SVM classifier...")
    svm = SVC(
        kernel='rbf',
        C=SVM_C,
        gamma=SVM_GAMMA,
        probability=True,
        class_weight='balanced',
        random_state=42
    )
    
    # Cross-validation
    logger.info(f"Running {CV_FOLDS}-fold stratified cross-validation...")
    unique_counts = np.bincount(y_enc)
    min_samples_per_class = int(unique_counts.min())
    actual_folds = min(CV_FOLDS, min_samples_per_class)
    
    if actual_folds >= 2:
        skf = StratifiedKFold(n_splits=actual_folds, shuffle=True, random_state=42)
        cv_scores = cross_val_score(svm, X_norm, y_enc, cv=skf, scoring='accuracy')
        logger.info(f"✅ Cross-validation accuracy: {cv_scores.mean()*100:.1f}% ± {cv_scores.std()*100:.1f}%")
        logger.info(f"   Per-fold: {[f'{s*100:.1f}%' for s in cv_scores]}")
    else:
        logger.warning(f"⚠️  Not enough samples for {CV_FOLDS}-fold CV")
        cv_scores = np.array([])
    
    # Train on full dataset
    logger.info("\nTraining final model on full dataset...")
    svm.fit(X_norm, y_enc)
    logger.info(f"✅ SVM trained")
    logger.info(f"   Support vectors: {len(svm.support_vectors_)}")
    logger.info(f"   Classes: {len(svm.classes_)}")
    
    return svm, le, cv_scores


def calculate_per_class_accuracy(svm: SVC, X_norm: np.ndarray, 
                                y: np.ndarray, le: LabelEncoder) -> Dict[str, float]:
    """
    Calculate training accuracy per person.
    
    Returns
    -------
    Dict[str, float]
        {person_name: accuracy}
    """
    y_pred = svm.predict(X_norm)
    y_actual = le.transform(y)
    
    per_class_acc = {}
    for class_idx, class_name in enumerate(le.classes_):
        mask = y_actual == class_idx
        if mask.sum() > 0:
            accuracy = (y_pred[mask] == class_idx).sum() / mask.sum()
            per_class_acc[class_name] = float(accuracy)
    
    return per_class_acc


def save_model_to_database(db: DatabaseConnection,
                          svm: SVC, le: LabelEncoder,
                          cv_scores: np.ndarray,
                          X_norm: np.ndarray, y: np.ndarray,
                          duration_seconds: float):
    """
    Serialize and save SVM model + LabelEncoder to database.
    
    Parameters
    ----------
    db : DatabaseConnection
        Database connection
    svm : SVC
        Trained SVM model
    le : LabelEncoder
        Fitted label encoder
    cv_scores : np.ndarray
        Cross-validation accuracy scores
    X_norm : np.ndarray
        Training embeddings used
    y : np.ndarray
        Training labels used
    duration_seconds : float
        Training time
    """
    logger.info("\nSaving model to database...")
    
    # Calculate per-class accuracy
    per_class_acc = calculate_per_class_accuracy(svm, X_norm, y, le)
    
    # SVM hyperparameters
    svm_params = {
        'C': SVM_C,
        'gamma': SVM_GAMMA,
        'kernel': 'rbf',
        'probability': True,
        'class_weight': 'balanced'
    }
    
    # CV metrics
    cv_accuracy = float(cv_scores.mean()) if len(cv_scores) > 0 else 0.0
    cv_std = float(cv_scores.std()) if len(cv_scores) > 0 else 0.0
    
    # Save to database
    version_number = db.save_model_version(
        svm_model=svm,
        label_encoder=le,
        cv_accuracy=cv_accuracy,
        cv_std=cv_std,
        per_class_accuracy=per_class_acc,
        svm_hyperparams=svm_params,
        num_training_samples=len(X_norm),
        training_duration_seconds=duration_seconds
    )
    
    logger.info(f"✅ Model saved to database as version {version_number}")
    logger.info(f"   Persons: {list(le.classes_)}")
    logger.info(f"   CV Accuracy: {cv_accuracy*100:.1f}%")
    logger.info(f"   Per-class accuracy:")
    for name, acc in per_class_acc.items():
        logger.info(f"     {name:20s} {acc*100:5.1f}%")
    
    return version_number


def train_svm(db: DatabaseConnection, include_unknown_labeled: bool = False):
    """
    Main function: Load embeddings, train SVM, save to database.
    
    Parameters
    ----------
    db : DatabaseConnection
        Database connection
    include_unknown_labeled : bool
        Include labeled unknown faces in training
    """
    logger.info("=" * 70)
    logger.info("SECTION D: TRAIN SVM FROM DATABASE")
    logger.info("=" * 70)
    logger.info(f"SVM Configuration:")
    logger.info(f"  C: {SVM_C}")
    logger.info(f"  Gamma: {SVM_GAMMA}")
    logger.info(f"  Include unknown faces: {include_unknown_labeled}")
    logger.info()
    
    start_time = time.time()
    
    try:
        # Load embeddings
        X, y, unique_persons = load_embeddings_for_training(
            db, include_unknown_labeled=include_unknown_labeled
        )
        
        # Normalize
        X_norm = normalize_embeddings(X)
        
        # Train SVM with CV
        svm, le, cv_scores = train_svm_with_cv(X_norm, y, unique_persons)
        
        # Save to database
        duration = time.time() - start_time
        version = save_model_to_database(db, svm, le, cv_scores, X_norm, y, duration)
        
        logger.info("\n" + "=" * 70)
        logger.info("SECTION D COMPLETE")
        logger.info(f"Model v{version} trained and saved")
        logger.info(f"Training time: {duration:.1f} seconds")
        logger.info("=" * 70)
        
        return version, svm, le
    
    except Exception as e:
        logger.error(f"❌ Error training SVM: {e}", exc_info=True)
        raise


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        from section_a_db_init import initialize_database
        db = initialize_database()
        
        # Train model
        version, svm, le = train_svm(db, include_unknown_labeled=False)
        
        logger.info(f"\n✅ SUCCESS: Model v{version} trained and saved to database")
        logger.info("Next: Run section_e_batch_inference.py for inference")
    
    except Exception as e:
        logger.error(f"❌ Error in Section D: {e}", exc_info=True)
        sys.exit(1)
