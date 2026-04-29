"""
Retraining service — launch background SVM training jobs.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import io
import logging
import threading
import time
import traceback

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, normalize
from sklearn.svm import SVC

import model_cache
from db import queries
from job_registry import create_job, update_job

logger = logging.getLogger(__name__)


def start_retraining_job(db) -> str:
    """
    Create a training job, launch it in a daemon thread, and return the job_id.

    Parameters
    ----------
    db:
        DatabaseConnection instance.

    Returns
    -------
    str
        UUID job_id that can be polled via the job registry.
    """
    job_id = create_job()
    update_job(job_id, status="running")
    thread = threading.Thread(target=_run_pipeline, args=(job_id, db), daemon=True)
    thread.start()
    return job_id


def _run_pipeline(job_id: str, db) -> None:
    """Background worker: train SVM and save to DB."""
    try:
        update_job(job_id, status="running", progress_pct=10, message="Loading embeddings...")
        embeddings_data = queries.get_embeddings_for_training(db, include_unknown_labeled=True)

        if len(embeddings_data) < 2:
            raise ValueError("Not enough training data (need at least 2 samples)")

        update_job(job_id, progress_pct=30, message="Normalizing embeddings...")
        X = np.array([e[0] for e in embeddings_data])
        y = [e[1] for e in embeddings_data]
        X_norm = normalize(X, norm="l2")

        update_job(job_id, progress_pct=60, message="Training SVM...")
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        svm = SVC(kernel="rbf", C=10, gamma="scale", probability=True)
        cv = StratifiedKFold(n_splits=min(5, len(set(y))))
        cv_scores = cross_val_score(svm, X_norm, y_encoded, cv=cv, scoring="accuracy")
        svm.fit(X_norm, y_encoded)
        cv_accuracy = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))

        update_job(job_id, progress_pct=90, message="Saving model...")
        t0 = time.time()
        model_buf = io.BytesIO()
        import joblib
        joblib.dump(svm, model_buf)
        model_bytes = model_buf.getvalue()

        le_buf = io.BytesIO()
        joblib.dump(le, le_buf)
        le_bytes = le_buf.getvalue()

        version_number = queries.get_next_version_number(db)
        svm_hyperparams = {"kernel": "rbf", "C": 10, "gamma": "scale"}
        queries.save_model_version(
            db,
            version_number,
            model_bytes,
            le_bytes,
            len(le.classes_),
            len(X_norm),
            cv_accuracy,
            cv_std,
            svm_hyperparams,
            time.time() - t0,
        )

        model_cache.refresh_model(svm, le, version_number)

        update_job(
            job_id,
            status="completed",
            progress_pct=100,
            message="Training complete",
            version_number=version_number,
            cv_accuracy=cv_accuracy,
            num_classes=len(le.classes_),
        )

    except Exception as exc:
        logger.error("Retraining job %s failed:\n%s", job_id, traceback.format_exc())
        update_job(job_id, status="failed", message=str(exc))
