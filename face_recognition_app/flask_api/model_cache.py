"""
In-memory model cache for the Flask API.

Holds the active SVM + LabelEncoder so they are loaded from the database
only once (or when explicitly refreshed), avoiding repeated DB round-trips
on every inference request.
"""

import io
import threading
from dataclasses import dataclass, field
from typing import Optional, Tuple

import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC


@dataclass
class ModelCache:
    svm: Optional[SVC] = None
    label_encoder: Optional[LabelEncoder] = None
    version_number: Optional[int] = None
    lock: threading.Lock = field(default_factory=threading.Lock)


# Module-level singleton
_cache = ModelCache()


def get_active_model(db_conn) -> Tuple[SVC, LabelEncoder]:
    """
    Return the cached (svm, label_encoder).

    On first call (or when the cache is empty) the active model is loaded
    from the ``model_versions`` table (``is_active = TRUE``), deserialized
    with joblib, stored in the cache, and returned.

    Parameters
    ----------
    db_conn:
        A ``DatabaseConnection`` instance (from
        ``face_recognition_app.database.db_connection``).

    Returns
    -------
    Tuple[SVC, LabelEncoder]

    Raises
    ------
    RuntimeError
        If no active model row is found in the database.
    """
    if _cache.svm is not None:
        return _cache.svm, _cache.label_encoder

    with _cache.lock:
        # Double-checked locking: another thread may have loaded while we waited
        if _cache.svm is not None:
            return _cache.svm, _cache.label_encoder

        raw_conn = db_conn.get_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute(
                "SELECT version_number, model_bytes, label_encoder_bytes "
                "FROM model_versions WHERE is_active = TRUE "
                "ORDER BY version_number DESC LIMIT 1"
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            db_conn.return_connection(raw_conn)

        if row is None:
            raise RuntimeError("No active model found in the database.")

        version_number, model_bytes, le_bytes = row

        if not model_bytes or not le_bytes:
            raise RuntimeError("Model bytes are empty — please train a model first.")

        svm: SVC = joblib.load(io.BytesIO(bytes(model_bytes)))
        label_encoder: LabelEncoder = joblib.load(io.BytesIO(bytes(le_bytes)))

        _cache.svm = svm
        _cache.label_encoder = label_encoder
        _cache.version_number = version_number

    return _cache.svm, _cache.label_encoder


def refresh_model(svm: SVC, le: LabelEncoder, version_number: int) -> None:
    """
    Atomically replace the cached model with a newly trained one.

    Parameters
    ----------
    svm:
        Freshly trained ``SVC`` instance.
    le:
        Fitted ``LabelEncoder`` instance.
    version_number:
        Version number of the new model.
    """
    with _cache.lock:
        _cache.svm = svm
        _cache.label_encoder = le
        _cache.version_number = version_number


def get_cached_version() -> Optional[int]:
    """Return the version number of the currently cached model, or None."""
    return _cache.version_number


def is_model_loaded() -> bool:
    """Return True if a model is currently held in the cache."""
    return _cache.svm is not None
