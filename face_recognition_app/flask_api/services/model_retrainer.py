"""
Model Retrainer Service — manages face recognition model retraining workflow.

This service provides a high-level interface for:
- Triggering model retraining jobs
- Training SVM classifiers with cross-validation
- Managing model versions and serialization
- Polling retraining job status
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import io
import logging
import threading
import time
import traceback
from typing import Dict, List, Optional

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, normalize
from sklearn.svm import SVC

import model_cache
from db import queries
from job_registry import create_job, update_job, get_job, job_to_dict

logger = logging.getLogger(__name__)


class ModelRetrainerService:
    """
    Service for managing face recognition model retraining.
    
    This service handles the complete retraining workflow:
    1. Creating retraining jobs with unique job IDs
    2. Fetching labeled face embeddings from the database
    3. Training SVM classifiers with 5-fold cross-validation
    4. Serializing trained models and storing metadata
    5. Providing status updates for polling
    
    Attributes
    ----------
    db_connection : DatabaseConnection
        Database connection instance for querying and storing data
    """
    
    def __init__(self, db_connection):
        """
        Initialize the ModelRetrainerService.
        
        Parameters
        ----------
        db_connection : DatabaseConnection
            Database connection instance
        """
        self.db = db_connection
    
    def trigger_retrain(self) -> str:
        """
        Create a retraining job and launch it in a background thread.
        
        This method:
        1. Generates a unique job_id using UUID
        2. Stores the job in the job registry with status 'queued'
        3. Launches a daemon thread to execute the training
        4. Returns the job_id for status polling
        
        Returns
        -------
        str
            UUID job_id that can be used to poll job status
            
        Examples
        --------
        >>> service = ModelRetrainerService(db)
        >>> job_id = service.trigger_retrain()
        >>> print(f"Retraining job started: {job_id}")
        """
        job_id = create_job()
        update_job(job_id, status="running")
        thread = threading.Thread(
            target=self._run_training_pipeline,
            args=(job_id,),
            daemon=True
        )
        thread.start()
        return job_id
    
    def get_retrain_status(self, job_id: str) -> Optional[Dict]:
        """
        Retrieve the current status of a retraining job.
        
        Parameters
        ----------
        job_id : str
            The UUID of the retraining job
            
        Returns
        -------
        Optional[Dict]
            Dictionary containing job status information:
            - job_id: str - The job identifier
            - status: str - Current status ('queued', 'running', 'completed', 'failed')
            - progress_pct: int - Progress percentage (0-100)
            - message: str - Human-readable status message
            - version_number: Optional[int] - Model version (when completed)
            - cv_accuracy: Optional[float] - Cross-validation accuracy (when completed)
            - num_classes: Optional[int] - Number of classes trained (when completed)
            
            Returns None if job_id is not found
            
        Examples
        --------
        >>> status = service.get_retrain_status(job_id)
        >>> if status:
        ...     print(f"Status: {status['status']}, Progress: {status['progress_pct']}%")
        """
        job = get_job(job_id)
        if job is None:
            return None
        return job_to_dict(job)
    
    def train_model(self, job_id: str) -> Dict:
        """
        Execute the complete model training process.
        
        This method performs the following steps:
        1. Fetch all labeled faces from the database
        2. Load face embeddings and labels
        3. Normalize embeddings using L2 normalization
        4. Encode labels using LabelEncoder
        5. Train SVM classifier with RBF kernel
        6. Perform 5-fold cross-validation
        7. Serialize model and label encoder
        8. Store model metadata in database
        9. Update job status
        
        Parameters
        ----------
        job_id : str
            The UUID of the retraining job
            
        Returns
        -------
        Dict
            Training results containing:
            - version_number: int - New model version number
            - cv_accuracy: float - Cross-validation accuracy
            - cv_std: float - Cross-validation standard deviation
            - num_classes: int - Number of classes in the model
            - num_training_samples: int - Total training samples used
            - training_duration: float - Training time in seconds
            
        Raises
        ------
        ValueError
            If insufficient training data (< 2 samples)
        Exception
            If training or serialization fails
            
        Examples
        --------
        >>> results = service.train_model(job_id)
        >>> print(f"Model v{results['version_number']} trained with "
        ...       f"{results['cv_accuracy']:.2%} accuracy")
        """
        try:
            # Step 1: Load embeddings
            update_job(
                job_id,
                status="running",
                progress_pct=10,
                message="Loading embeddings..."
            )
            embeddings_data = queries.get_embeddings_for_training(
                self.db,
                include_unknown_labeled=True
            )
            
            if len(embeddings_data) < 2:
                raise ValueError(
                    "Not enough training data (need at least 2 samples)"
                )
            
            # Step 2: Prepare training data
            update_job(
                job_id,
                progress_pct=30,
                message="Normalizing embeddings..."
            )
            X = np.array([e[0] for e in embeddings_data])
            y = [e[1] for e in embeddings_data]
            X_norm = normalize(X, norm="l2")
            
            # Step 3: Encode labels
            le = LabelEncoder()
            y_encoded = le.fit_transform(y)
            
            # Step 4: Train SVM with cross-validation
            update_job(
                job_id,
                progress_pct=60,
                message="Training SVM classifier..."
            )
            svm = SVC(kernel="rbf", C=10, gamma="scale", probability=True)
            
            # Use 5-fold cross-validation (or fewer if not enough samples)
            n_splits = min(5, len(set(y)))
            cv = StratifiedKFold(n_splits=n_splits)
            cv_scores = cross_val_score(
                svm, X_norm, y_encoded, cv=cv, scoring="accuracy"
            )
            
            # Fit the final model on all data
            svm.fit(X_norm, y_encoded)
            
            cv_accuracy = float(np.mean(cv_scores))
            cv_std = float(np.std(cv_scores))
            
            # Step 5: Serialize model
            update_job(
                job_id,
                progress_pct=90,
                message="Saving model..."
            )
            training_start = time.time()
            
            # Serialize SVM model
            model_buf = io.BytesIO()
            import joblib
            joblib.dump(svm, model_buf)
            model_bytes = model_buf.getvalue()
            
            # Serialize label encoder
            le_buf = io.BytesIO()
            joblib.dump(le, le_buf)
            le_bytes = le_buf.getvalue()
            
            # Step 6: Store model version in database
            version_number = queries.get_next_version_number(self.db)
            svm_hyperparams = {"kernel": "rbf", "C": 10, "gamma": "scale"}
            training_duration = time.time() - training_start
            
            queries.save_model_version(
                self.db,
                version_number,
                model_bytes,
                le_bytes,
                len(le.classes_),
                len(X_norm),
                cv_accuracy,
                cv_std,
                svm_hyperparams,
                training_duration,
            )
            
            # Step 7: Refresh model cache
            model_cache.refresh_model(svm, le, version_number)
            
            # Step 8: Update job status to completed
            update_job(
                job_id,
                status="completed",
                progress_pct=100,
                message="Training complete",
                version_number=version_number,
                cv_accuracy=cv_accuracy,
                num_classes=len(le.classes_),
            )
            
            return {
                "version_number": version_number,
                "cv_accuracy": cv_accuracy,
                "cv_std": cv_std,
                "num_classes": len(le.classes_),
                "num_training_samples": len(X_norm),
                "training_duration": training_duration,
            }
            
        except Exception as exc:
            logger.error(
                "Retraining job %s failed:\n%s",
                job_id,
                traceback.format_exc()
            )
            update_job(job_id, status="failed", message=str(exc))
            raise
    
    def _run_training_pipeline(self, job_id: str) -> None:
        """
        Background worker that executes the training pipeline.
        
        This method is run in a daemon thread and handles all exceptions
        to ensure the job status is updated appropriately.
        
        Parameters
        ----------
        job_id : str
            The UUID of the retraining job
        """
        try:
            self.train_model(job_id)
        except Exception as exc:
            # Exception already logged and job status updated in train_model
            pass
