"""
SQL helper functions wrapping DatabaseConnection for all Flask API DB operations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import urllib.parse
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from face_recognition_app.database.db_connection import DatabaseConnection
from face_recognition_app.flask_api.config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db_connection() -> DatabaseConnection:
    """
    Return the shared DatabaseConnection instance from Flask app context.
    
    This ensures we reuse the same connection pool across all requests,
    avoiding the 'unkeyed connection' error that occurs when each request
    creates its own pool.
    """
    from flask import current_app
    
    # Try to get the shared pool from Flask app context
    if current_app and 'DB_CONNECTION_POOL' in current_app.config:
        return current_app.config['DB_CONNECTION_POOL']
    
    # Fallback for non-Flask contexts (CLI scripts, tests, etc.)
    # Create a new connection pool instance
    parsed = urllib.parse.urlparse(config.DATABASE_URL)
    return DatabaseConnection(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        database=(parsed.path or "/face_recognition").lstrip("/"),
        user=parsed.username or "admin",
        password=parsed.password or "admin",
    )


# ---------------------------------------------------------------------------
# Model versions
# ---------------------------------------------------------------------------

def get_active_model_version(conn: DatabaseConnection) -> Optional[Dict]:
    """SELECT from model_versions WHERE is_active=TRUE. Returns row dict or None."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, version_number, num_classes, num_training_samples, "
            "cross_validation_accuracy, cross_validation_std, trained_at, "
            "is_active, svm_hyperparams, per_class_accuracy "
            "FROM model_versions WHERE is_active = TRUE "
            "ORDER BY version_number DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [
            "id", "version_number", "num_classes", "num_training_samples",
            "cross_validation_accuracy", "cross_validation_std", "trained_at",
            "is_active", "svm_hyperparams", "per_class_accuracy",
        ]
        return dict(zip(cols, row))
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_all_model_versions(conn: DatabaseConnection) -> List[Dict]:
    """SELECT all from model_versions ORDER BY version_number DESC."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, version_number, num_classes, num_training_samples, "
            "cross_validation_accuracy, cross_validation_std, trained_at, "
            "is_active "
            "FROM model_versions ORDER BY version_number DESC"
        )
        cols = [
            "id", "version_number", "num_classes", "num_training_samples",
            "cross_validation_accuracy", "cross_validation_std", "trained_at",
            "is_active",
        ]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def activate_model_version(conn: DatabaseConnection, version_number: int) -> None:
    """Set is_active=TRUE for version_number, FALSE for all others."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute("UPDATE model_versions SET is_active = FALSE")
        cursor.execute(
            "UPDATE model_versions SET is_active = TRUE WHERE version_number = %s",
            (version_number,),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Video sessions
# ---------------------------------------------------------------------------

def insert_video_session(conn: DatabaseConnection, session_id: str) -> None:
    """INSERT into video_sessions with the given UUID session_id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO video_sessions (id) VALUES (%s::uuid)",
            (session_id,),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def end_video_session(
    conn: DatabaseConnection,
    session_id: str,
    end_time: Any,
    total_frames: int,
) -> None:
    """UPDATE video_sessions SET end_time, total_frames WHERE id=session_id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE video_sessions SET end_time = %s, total_frames = %s WHERE id = %s::uuid",
            (end_time, total_frames, session_id),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------

def insert_frame(
    conn: DatabaseConnection,
    session_id: str,
    frame_number: int,
    width: int,
    height: int,
    timestamp_ms: Optional[int] = None,
) -> int:
    """INSERT into frames, return frame id. If duplicate, return existing frame id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        # Note: timestamp_ms parameter is ignored as the frames table uses TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        # Use ON CONFLICT to handle duplicate (session_id, frame_number) pairs
        # If conflict occurs, just return the existing frame's id
        cursor.execute(
            "INSERT INTO frames (video_session_id, frame_number, width, height) "
            "VALUES (%s::uuid, %s, %s, %s) "
            "ON CONFLICT (video_session_id, frame_number) "
            "DO UPDATE SET video_session_id = EXCLUDED.video_session_id "
            "RETURNING id",
            (session_id, frame_number, width, height),
        )
        frame_id = cursor.fetchone()[0]
        db_conn.commit()
        return frame_id
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Detections
# ---------------------------------------------------------------------------

def insert_detection(
    conn: DatabaseConnection,
    frame_id: int,
    person_id: Optional[int],
    unknown_face_id: Optional[int],
    bbox_x1: int,
    bbox_y1: int,
    bbox_x2: int,
    bbox_y2: int,
    svm_prediction: str,
    svm_probability: float,
    detection_confidence: float,
) -> None:
    """INSERT into detections."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO detections "
            "(frame_id, person_id, unknown_face_id, "
            "detection_bbox_x1, detection_bbox_y1, detection_bbox_x2, detection_bbox_y2, "
            "svm_prediction, svm_probability, detection_confidence) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                frame_id, person_id, unknown_face_id,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                svm_prediction, svm_probability, detection_confidence,
            ),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Unknown faces
# ---------------------------------------------------------------------------

def insert_unknown_face(
    conn: DatabaseConnection,
    embedding: Any,
    source_image_path: str,
    frame_id: Optional[int],
    detection_confidence: float,
    svm_prediction: str,
    svm_probability: float,
    source_video_id: Optional[int] = None,
    frame_timestamp: Optional[float] = None,
    frame_number: Optional[int] = None,
) -> int:
    """INSERT into unknown_faces with video source tracking, return id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        cursor.execute(
            "INSERT INTO unknown_faces "
            "(embedding, source_image_path, source_frame_id, "
            "detection_confidence, svm_prediction, svm_probability, status, "
            "source_video_id, frame_timestamp, frame_number) "
            "VALUES (%s::vector, %s, %s, %s, %s, %s, 'pending', %s, %s, %s) RETURNING id",
            (
                embedding, source_image_path, frame_id,
                detection_confidence, svm_prediction, svm_probability,
                source_video_id, frame_timestamp, frame_number,
            ),
        )
        face_id = cursor.fetchone()[0]
        db_conn.commit()
        return face_id
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_unknown_faces_paginated(
    conn: DatabaseConnection,
    status: Optional[str],
    page: int,
    page_size: int,
) -> Tuple[List[Dict], int]:
    """SELECT unknown faces with LIMIT/OFFSET. Returns (items, total)."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        offset = (page - 1) * page_size

        where_clause = "WHERE status = %s" if status else ""
        params_count = (status,) if status else ()
        params_page = (status, page_size, offset) if status else (page_size, offset)

        cursor.execute(
            f"SELECT COUNT(*) FROM unknown_faces {where_clause}",
            params_count,
        )
        total = cursor.fetchone()[0]

        cursor.execute(
            f"SELECT id, source_image_path, svm_prediction, svm_probability, "
            f"detection_confidence, status, created_at "
            f"FROM unknown_faces {where_clause} "
            f"ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params_page,
        )
        cols = [
            "id", "source_image_path", "svm_prediction", "svm_probability",
            "detection_confidence", "status", "created_at",
        ]
        items = [dict(zip(cols, row)) for row in cursor.fetchall()]
        return items, total
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_unknown_face_by_id(conn: DatabaseConnection, face_id: int) -> Optional[Dict]:
    """SELECT single unknown face by id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, embedding, source_image_path, svm_prediction, svm_probability, "
            "detection_confidence, status, assigned_person_id, labeled_by_user, "
            "labeled_at, created_at "
            "FROM unknown_faces WHERE id = %s",
            (face_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [
            "id", "embedding", "source_image_path", "svm_prediction", "svm_probability",
            "detection_confidence", "status", "assigned_person_id", "labeled_by_user",
            "labeled_at", "created_at",
        ]
        return dict(zip(cols, row))
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def update_unknown_face_label(
    conn: DatabaseConnection,
    face_id: int,
    person_id: int,
    labeled_by: str,
) -> None:
    """UPDATE unknown_faces SET status='labeled', assigned_person_id, labeled_by_user."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE unknown_faces SET status = 'labeled', assigned_person_id = %s, "
            "labeled_by_user = %s, labeled_at = NOW(), updated_at = NOW() "
            "WHERE id = %s",
            (person_id, labeled_by, face_id),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def label_unknown_face(conn: DatabaseConnection, face_id: int, person_id: int, labeled_by: str) -> None:
    """Alias for update_unknown_face_label — updates unknown_faces status to 'labeled'."""
    update_unknown_face_label(conn, face_id, person_id, labeled_by)


def update_unknown_face_reject(
    conn: DatabaseConnection,
    face_id: int,
    rejected_by: str,
) -> None:
    """UPDATE unknown_faces SET status='rejected'."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE unknown_faces SET status = 'rejected', "
            "labeled_by_user = %s, updated_at = NOW() WHERE id = %s",
            (rejected_by, face_id),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def reject_unknown_face(conn: DatabaseConnection, face_id: int, rejected_by: str) -> None:
    """Alias for update_unknown_face_reject — updates unknown_faces status to 'rejected'."""
    update_unknown_face_reject(conn, face_id, rejected_by)


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

def upsert_person(conn: DatabaseConnection, name: str) -> int:
    """INSERT OR SELECT person by name, return person_id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT id FROM people WHERE name = %s", (name,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute(
            "INSERT INTO people (name) VALUES (%s) RETURNING id",
            (name,),
        )
        person_id = cursor.fetchone()[0]
        db_conn.commit()
        return person_id
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def insert_person(
    conn: DatabaseConnection,
    name: str,
    description: Optional[str],
    role: Optional[str],
) -> Dict:
    """INSERT into people, return created row."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO people (name, description, role) VALUES (%s, %s, %s) "
            "RETURNING id, name, description, role, created_at",
            (name, description, role),
        )
        row = cursor.fetchone()
        db_conn.commit()
        cols = ["id", "name", "description", "role", "created_at"]
        return dict(zip(cols, row))
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_people_with_face_counts(conn: DatabaseConnection) -> List[Dict]:
    """JOIN people + COUNT(faces) grouped by person."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT p.id, p.name, p.description, p.role, p.created_at, "
            "COUNT(f.id) AS face_count "
            "FROM people p LEFT JOIN faces f ON p.id = f.person_id "
            "GROUP BY p.id, p.name, p.description, p.role, p.created_at "
            "ORDER BY p.name"
        )
        cols = ["id", "name", "description", "role", "created_at", "face_count"]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Faces (embeddings)
# ---------------------------------------------------------------------------

def insert_face_from_unknown(
    conn: DatabaseConnection,
    person_id: int,
    embedding: Any,
    source_type: str = "unknown_labeled",
    image_path: str = "",
    unknown_face_id: Optional[int] = None,
    person_name: str = "",
) -> None:
    """INSERT into faces with the given embedding.
    
    If image_path is empty, generates a unique path and saves the face image
    from unknown_faces to labeled_face_images directory for future use.
    
    Args:
        conn: Database connection
        person_id: ID of the person
        embedding: Face embedding vector
        source_type: Source type (default: "unknown_labeled")
        image_path: Path to image file (if empty, will be generated)
        unknown_face_id: ID of the unknown face (used to copy image file)
        person_name: Name of the person (used in filename)
    """
    import uuid
    from services import image_service
    
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        # Generate unique image_path if empty
        if not image_path or image_path.strip() == "":
            if unknown_face_id and person_name:
                # Save the actual image file to labeled_face_images directory
                try:
                    image_path = image_service.save_labeled_face_image(
                        unknown_face_id, person_id, person_name
                    )
                except Exception as e:
                    # If image saving fails, use virtual path as fallback
                    logger.warning(f"Failed to save labeled face image: {e}")
                    image_path = f"labeled_face_images/{person_name}_{person_id}_{uuid.uuid4()}.jpg"
            else:
                # Fallback: generate virtual path
                image_path = f"labeled_face_images/person_{person_id}_{uuid.uuid4()}.jpg"
        
        cursor.execute(
            "INSERT INTO faces (person_id, image_path, embedding, source_type) "
            "VALUES (%s, %s, %s::vector, %s)",
            (person_id, image_path, embedding, source_type),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def get_dashboard_stats(conn: DatabaseConnection) -> Dict:
    """Aggregate query for dashboard KPIs."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM people")
        total_people = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM faces")
        total_faces = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM unknown_faces WHERE status = 'pending'")
        pending_unknowns = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM unknown_faces WHERE status = 'labeled'")
        labeled_unknowns = cursor.fetchone()[0]

        cursor.execute(
            "SELECT version_number, cross_validation_accuracy "
            "FROM model_versions WHERE is_active = TRUE LIMIT 1"
        )
        model_row = cursor.fetchone()
        active_model_version = model_row[0] if model_row else None
        active_model_accuracy = model_row[1] if model_row else None

        cursor.execute(
            "SELECT COUNT(*) FROM detections d "
            "JOIN frames f ON d.frame_id = f.id "
            "WHERE f.created_at >= CURRENT_DATE"
        )
        total_detections_today = cursor.fetchone()[0]

        return {
            "total_people": total_people,
            "total_faces": total_faces,
            "pending_unknowns": pending_unknowns,
            "labeled_unknowns": labeled_unknowns,
            "active_model_version": active_model_version,
            "active_model_accuracy": active_model_accuracy,
            "total_detections_today": total_detections_today,
        }
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Model versions — additional helpers
# ---------------------------------------------------------------------------

def get_next_version_number(conn: DatabaseConnection) -> int:
    """Return MAX(version_number)+1 from model_versions, or 1 if table is empty."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM model_versions")
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def save_model_version(
    conn: DatabaseConnection,
    version_number: int,
    model_bytes: bytes,
    label_encoder_bytes: bytes,
    num_classes: int,
    num_training_samples: int,
    cv_accuracy: float,
    cv_std: float,
    svm_hyperparams: Any,
    training_duration: float,
) -> int:
    """
    INSERT into model_versions with is_active=TRUE, deactivate all others.
    Returns the new row id.
    """
    import json as _json

    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        # Deactivate existing active versions
        cursor.execute("UPDATE model_versions SET is_active = FALSE")
        cursor.execute(
            "INSERT INTO model_versions "
            "(version_number, model_bytes, label_encoder_bytes, num_classes, "
            "num_training_samples, trained_at, training_duration_seconds, "
            "cross_validation_accuracy, cross_validation_std, "
            "svm_hyperparams, is_active) "
            "VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s::jsonb, TRUE) "
            "RETURNING id",
            (
                version_number,
                model_bytes,
                label_encoder_bytes,
                num_classes,
                num_training_samples,
                training_duration,
                cv_accuracy,
                cv_std,
                _json.dumps(svm_hyperparams) if not isinstance(svm_hyperparams, str) else svm_hyperparams,
            ),
        )
        row_id = cursor.fetchone()[0]
        db_conn.commit()
        return row_id
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Embeddings for training
# ---------------------------------------------------------------------------

def get_embeddings_for_training(
    conn: DatabaseConnection,
    include_unknown_labeled: bool = True,
) -> List[Tuple[Any, str]]:
    """
    Return list of (embedding_vector, person_name) tuples for SVM training.
    Includes source_type='training' always; adds 'unknown_labeled' when flag is True.
    """
    db_conn = conn.get_connection()
    cursor = None
    try:
        # Try to register pgvector type for proper handling
        try:
            from pgvector.psycopg2 import register_vector
            register_vector(db_conn)
        except (ImportError, ModuleNotFoundError):
            # pgvector not installed, will handle string format below
            pass
        except Exception:
            # Other registration errors, continue anyway
            pass
        
        cursor = db_conn.cursor()
        if include_unknown_labeled:
            cursor.execute(
                "SELECT f.embedding, p.name FROM faces f "
                "JOIN people p ON f.person_id = p.id "
                "WHERE f.source_type IN ('training', 'unknown_labeled') "
                "ORDER BY p.id, f.id"
            )
        else:
            cursor.execute(
                "SELECT f.embedding, p.name FROM faces f "
                "JOIN people p ON f.person_id = p.id "
                "WHERE f.source_type = 'training' "
                "ORDER BY p.id, f.id"
            )
        
        # Convert pgvector result to numpy array
        # After register_vector, row[0] will be a list-like object
        # Without register_vector, row[0] will be a string representation
        results = []
        for row in cursor.fetchall():
            try:
                embedding_data = row[0]
                
                # Handle string representation (when pgvector not registered)
                if isinstance(embedding_data, str):
                    # Parse string representation: "[0.1, 0.2, ...]"
                    import json
                    embedding_data = json.loads(embedding_data)
                # Handle list or array (already in correct format)
                elif isinstance(embedding_data, (list, np.ndarray)):
                    pass  # Already in correct format
                else:
                    # Convert other iterable types to list
                    embedding_data = list(embedding_data)
                
                # Create numpy array with float64 dtype
                embedding_array = np.array(embedding_data, dtype=np.float64)
                results.append((embedding_array, row[1]))
            except Exception as e:
                raise ValueError(f"Unable to parse embedding data for person {row[1]}: {e}")
        
        return results
    finally:
        if cursor is not None:
            cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Videos
# ---------------------------------------------------------------------------

def insert_video(
    conn: DatabaseConnection,
    filename: str,
    file_path: str,
    file_size_bytes: int,
    video_hash: str,
    duration_seconds: Optional[float],
    fps: Optional[float],
    width: Optional[int],
    height: Optional[int],
) -> int:
    """INSERT into videos, return new id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO videos "
            "(filename, file_path, file_size_bytes, video_hash, "
            "duration_seconds, fps, width, height) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (filename, file_path, file_size_bytes, video_hash,
             duration_seconds, fps, width, height),
        )
        video_id = cursor.fetchone()[0]
        db_conn.commit()
        return video_id
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_video_by_hash(conn: DatabaseConnection, video_hash: str) -> Optional[Dict]:
    """SELECT * FROM videos WHERE video_hash = %s. Returns dict or None."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, filename, file_path, file_size_bytes, video_hash, "
            "duration_seconds, fps, width, height, status, uploaded_at, "
            "last_processed_at, unique_unknowns, unique_known "
            "FROM videos WHERE video_hash = %s",
            (video_hash,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [
            "id", "filename", "file_path", "file_size_bytes", "video_hash",
            "duration_seconds", "fps", "width", "height", "status", "uploaded_at",
            "last_processed_at", "unique_unknowns", "unique_known",
        ]
        return dict(zip(cols, row))
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_video_by_id(conn: DatabaseConnection, video_id: int) -> Optional[Dict]:
    """SELECT * FROM videos WHERE id = %s. Returns dict or None."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, filename, file_path, file_size_bytes, video_hash, "
            "duration_seconds, fps, width, height, status, uploaded_at, "
            "last_processed_at, unique_unknowns, unique_known "
            "FROM videos WHERE id = %s",
            (video_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [
            "id", "filename", "file_path", "file_size_bytes", "video_hash",
            "duration_seconds", "fps", "width", "height", "status", "uploaded_at",
            "last_processed_at", "unique_unknowns", "unique_known",
        ]
        return dict(zip(cols, row))
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def list_videos(
    conn: DatabaseConnection,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
) -> Tuple[List[Dict], int]:
    """SELECT videos with LIMIT/OFFSET ORDER BY uploaded_at DESC. Returns (items, total)."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        offset = (page - 1) * page_size

        # Build WHERE clause for status filter
        where_clause = ""
        params_count = []
        params_list = []
        
        if status:
            where_clause = "WHERE status = %s"
            params_count = [status]
            params_list = [status]

        # Get total count
        count_query = f"SELECT COUNT(*) FROM videos {where_clause}"
        cursor.execute(count_query, params_count)
        total = cursor.fetchone()[0]

        # Get paginated results
        list_query = (
            f"SELECT id, filename, file_path, file_size_bytes, video_hash, "
            f"duration_seconds, fps, width, height, status, uploaded_at, "
            f"last_processed_at, unique_unknowns, unique_known "
            f"FROM videos {where_clause} ORDER BY uploaded_at DESC LIMIT %s OFFSET %s"
        )
        params_list.extend([page_size, offset])
        cursor.execute(list_query, params_list)
        
        cols = [
            "id", "filename", "file_path", "file_size_bytes", "video_hash",
            "duration_seconds", "fps", "width", "height", "status", "uploaded_at",
            "last_processed_at", "unique_unknowns", "unique_known",
        ]
        items = [dict(zip(cols, row)) for row in cursor.fetchall()]
        return items, total
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Video jobs
# ---------------------------------------------------------------------------

def insert_video_job(conn: DatabaseConnection, job_id: str, video_id: int) -> None:
    """INSERT INTO video_jobs (job_id, video_id, status) VALUES (%s, %s, 'queued')."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO video_jobs (job_id, video_id, status) VALUES (%s, %s, 'queued')",
            (job_id, video_id),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_video_job(conn: DatabaseConnection, job_id: str) -> Optional[Dict]:
    """SELECT * FROM video_jobs WHERE job_id = %s. Returns dict or None."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, job_id, video_id, status, "
            "progress_pct, frames_processed, total_frames, message, "
            "unique_unknowns, unique_known, created_at, updated_at "
            "FROM video_jobs WHERE job_id = %s",
            (job_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [
            "id", "job_id", "video_id", "status",
            "progress_pct", "frames_processed", "total_frames", "message",
            "unique_unknowns", "unique_known", "created_at", "updated_at",
        ]
        return dict(zip(cols, row))
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def update_video_job_status(
    conn: DatabaseConnection,
    job_id: str,
    status: str,
    progress_pct: int = 0,
    frames_processed: int = 0,
    total_frames: int = 0,
    message: Optional[str] = None,
    unique_unknowns: int = 0,
    unique_known: int = 0,
) -> None:
    """UPDATE video_jobs SET all fields WHERE job_id = %s.
    Updates updated_at timestamp automatically.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE video_jobs SET status = %s, progress_pct = %s, "
            "frames_processed = %s, total_frames = %s, message = %s, "
            "unique_unknowns = %s, unique_known = %s, "
            "updated_at = NOW() "
            "WHERE job_id = %s",
            (status, progress_pct, frames_processed, total_frames, message,
             unique_unknowns, unique_known, job_id),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def update_video_record_status(
    conn: DatabaseConnection,
    video_id: int,
    status: str,
    last_processed_at: Any = None,
    unique_unknowns: int = 0,
    unique_known: int = 0,
) -> None:
    """UPDATE videos SET status, last_processed_at, unique_unknowns, unique_known WHERE id = %s."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE videos SET status = %s, last_processed_at = %s, "
            "unique_unknowns = %s, unique_known = %s WHERE id = %s",
            (status, last_processed_at, unique_unknowns, unique_known, video_id),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def delete_video(conn: DatabaseConnection, video_id: int) -> None:
    """
    DELETE video and all associated data.
    
    Deletes:
    - Video record from videos table
    - Associated video_jobs (cascade)
    - Associated video_detections (cascade)
    - Associated timeline_entries (cascade)
    
    Args:
        conn: Database connection
        video_id: ID of the video to delete
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        
        # Delete video (cascade will handle related records if foreign keys are set up)
        # Otherwise, we need to manually delete related records first
        
        # Delete timeline entries
        cursor.execute("DELETE FROM timeline_entries WHERE video_id = %s", (video_id,))
        
        # Delete video detections
        cursor.execute("DELETE FROM video_detections WHERE video_id = %s", (video_id,))
        
        # Delete video jobs
        cursor.execute("DELETE FROM video_jobs WHERE video_id = %s", (video_id,))
        
        # Delete the video record itself
        cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
        
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Video detections
# ---------------------------------------------------------------------------

def get_video_detections(conn: DatabaseConnection, video_id: int) -> List[Dict]:
    """
    Query video_detections table for all face detections in the given video.
    
    Returns list of dicts with frame_timestamp_ms, frame_number, and nested detections array.
    Each detection: bbox (x1,y1,x2,y2), name (person name or 'Unknown'),
    confidence (recognition_confidence), detection_confidence.
    
    This is used by the video playback feature to show bounding boxes on the video.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()

        # Query video_detections table directly
        cursor.execute(
            "SELECT frame_number, timestamp, person_name, "
            "bbox_x1, bbox_y1, bbox_x2, bbox_y2, "
            "recognition_confidence, detection_confidence "
            "FROM video_detections "
            "WHERE video_id = %s "
            "ORDER BY frame_number ASC, id ASC",
            (video_id,),
        )
        rows = cursor.fetchall()

        # Group detections by frame
        frames: Dict[int, Dict] = {}
        for (frame_number, timestamp, person_name, x1, y1, x2, y2,
             recognition_confidence, detection_confidence) in rows:
            
            # Convert timestamp (in seconds) to milliseconds
            timestamp_ms = int(timestamp * 1000) if timestamp is not None else 0
            
            if frame_number not in frames:
                frames[frame_number] = {
                    "frame_timestamp_ms": timestamp_ms,
                    "frame_id": frame_number,  # Use frame_number as frame_id for compatibility
                    "detections": [],
                }
            
            frames[frame_number]["detections"].append({
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "name": person_name if person_name else "Unknown",
                "confidence": float(recognition_confidence) if recognition_confidence is not None else 0.0,
                "detection_confidence": float(detection_confidence) if detection_confidence is not None else 0.0,
            })

        return list(frames.values())
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def insert_video_detection(
    conn: DatabaseConnection,
    video_id: int,
    frame_number: int,
    timestamp: float,
    person_id: Optional[int],
    person_name: str,
    bbox_x1: int,
    bbox_y1: int,
    bbox_x2: int,
    bbox_y2: int,
    recognition_confidence: float,
    detection_confidence: float,
    is_unknown: bool,
) -> int:
    """INSERT into video_detections, return id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO video_detections "
            "(video_id, frame_number, timestamp, person_id, person_name, "
            "bbox_x1, bbox_y1, bbox_x2, bbox_y2, "
            "recognition_confidence, detection_confidence, is_unknown) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (
                video_id, frame_number, timestamp, person_id, person_name,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                recognition_confidence, detection_confidence, is_unknown,
            ),
        )
        detection_id = cursor.fetchone()[0]
        db_conn.commit()
        return detection_id
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_video_session_face_counts(conn: DatabaseConnection, video_session_id: str) -> Dict:
    """
    Count unique unknown faces and unique known persons for a session.
    Returns {'unique_unknowns': int, 'unique_known': int}.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()

        cursor.execute(
            "SELECT COUNT(DISTINCT d.unknown_face_id) "
            "FROM detections d "
            "JOIN frames f ON d.frame_id = f.id "
            "WHERE f.video_session_id = %s::uuid "
            "AND d.unknown_face_id IS NOT NULL",
            (video_session_id,),
        )
        unique_unknowns = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(DISTINCT d.person_id) "
            "FROM detections d "
            "JOIN frames f ON d.frame_id = f.id "
            "WHERE f.video_session_id = %s::uuid "
            "AND d.person_id IS NOT NULL",
            (video_session_id,),
        )
        unique_known = cursor.fetchone()[0]

        return {"unique_unknowns": int(unique_unknowns), "unique_known": int(unique_known)}
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_video_frames_breakdown(conn: DatabaseConnection, video_id: int) -> List[Dict]:
    """
    Return frame-by-frame breakdown with aggregated detections for a video.
    
    Returns list of dicts with:
    - frame_number: int
    - timestamp_ms: int
    - thumbnail_path: str (image_path from frames table)
    - detections: list of dicts with person_id, person_name, bbox, confidence
    
    Uses PostgreSQL json_agg to aggregate detections per frame.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        
        # Find the most recent video_session_id for this video
        cursor.execute(
            "SELECT video_session_id FROM video_jobs "
            "WHERE video_id = %s AND video_session_id IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (video_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return []
        video_session_id = row[0]
        
        # Query frames with aggregated detections
        cursor.execute(
            """
            SELECT 
                f.frame_number,
                f.timestamp_ms,
                f.image_path,
                json_agg(
                    json_build_object(
                        'person_id', d.person_id,
                        'person_name', COALESCE(p.name, 'Unknown'),
                        'bbox', ARRAY[d.detection_bbox_x1, d.detection_bbox_y1, 
                                      d.detection_bbox_x2, d.detection_bbox_y2],
                        'confidence', d.svm_probability
                    )
                ) FILTER (WHERE d.id IS NOT NULL) as detections
            FROM frames f
            LEFT JOIN detections d ON d.frame_id = f.id
            LEFT JOIN people p ON d.person_id = p.id
            WHERE f.video_session_id = %s::uuid
            GROUP BY f.frame_number, f.timestamp_ms, f.image_path
            ORDER BY f.frame_number
            """,
            (video_session_id,),
        )
        
        results = []
        for row in cursor.fetchall():
            frame_number, timestamp_ms, image_path, detections_json = row
            results.append({
                "frame_number": frame_number,
                "timestamp_ms": timestamp_ms if timestamp_ms is not None else 0,
                "thumbnail_path": image_path if image_path else "",
                "detections": detections_json if detections_json else [],
            })
        
        return results
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_video_detections_with_frames(conn: DatabaseConnection, video_id: int) -> List[Dict]:
    """
    Query detections with frame metadata for video annotation.
    
    Returns list of dicts with:
    - frame_number: int
    - timestamp_ms: int
    - person_id: int or None
    - person_name: str (person name or 'Unknown')
    - bbox_x1, bbox_y1, bbox_x2, bbox_y2: int (bounding box coordinates)
    - confidence: float (svm_probability)
    
    Used for generating video with bounding boxes overlaid.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        
        # Find the most recent video_session_id for this video
        cursor.execute(
            "SELECT video_session_id FROM video_jobs "
            "WHERE video_id = %s AND video_session_id IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (video_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return []
        video_session_id = row[0]
        
        cursor.execute(
            """
            SELECT f.frame_number, f.timestamp_ms, d.person_id, p.name,
                   d.detection_bbox_x1, d.detection_bbox_y1,
                   d.detection_bbox_x2, d.detection_bbox_y2,
                   d.svm_probability
            FROM detections d
            JOIN frames f ON d.frame_id = f.id
            LEFT JOIN people p ON d.person_id = p.id
            WHERE f.video_session_id = %s::uuid
            ORDER BY f.frame_number, d.id
            """,
            (video_session_id,),
        )
        
        results = []
        for row in cursor.fetchall():
            frame_number, timestamp_ms, person_id, person_name, x1, y1, x2, y2, confidence = row
            results.append({
                "frame_number": frame_number,
                "timestamp_ms": timestamp_ms if timestamp_ms is not None else 0,
                "person_id": person_id,
                "person_name": person_name if person_name else "Unknown",
                "bbox_x1": x1,
                "bbox_y1": y1,
                "bbox_x2": x2,
                "bbox_y2": y2,
                "confidence": float(confidence) if confidence is not None else 0.0,
            })
        
        return results
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_all_unknown_face_embeddings(conn: DatabaseConnection) -> List[Dict]:
    """
    Get all unknown face embeddings for deduplication comparison.
    
    Returns list of dicts with:
    - id: int (unknown face ID)
    - embedding: list (face embedding vector)
    
    Used for comparing new unknown faces against existing ones to prevent duplicates.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, embedding FROM unknown_faces WHERE status = 'pending'"
        )
        
        results = []
        for row in cursor.fetchall():
            face_id, embedding = row
            results.append({
                "id": face_id,
                "embedding": embedding if isinstance(embedding, list) else list(embedding),
            })
        
        return results
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Timeline entries
# ---------------------------------------------------------------------------

def get_video_detections_for_timeline(
    conn: DatabaseConnection, video_id: int
) -> List[Dict]:
    """
    Query video_detections for timeline generation.
    
    Returns list of dicts with:
    - frame_number: int
    - timestamp: float (seconds)
    - person_id: int or None
    - person_name: str
    - recognition_confidence: float
    
    Ordered by frame_number for consecutive detection grouping.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT frame_number, timestamp, person_id, person_name, recognition_confidence
            FROM video_detections
            WHERE video_id = %s
            ORDER BY frame_number ASC
            """,
            (video_id,),
        )
        
        results = []
        for row in cursor.fetchall():
            frame_number, timestamp, person_id, person_name, recognition_confidence = row
            results.append({
                "frame_number": frame_number,
                "timestamp": timestamp,
                "person_id": person_id,
                "person_name": person_name,
                "recognition_confidence": recognition_confidence,
            })
        
        return results
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def insert_timeline_entry(
    conn: DatabaseConnection,
    video_id: int,
    person_id: Optional[int],
    person_name: str,
    start_time: float,
    end_time: float,
    detection_count: int,
    avg_confidence: float,
) -> int:
    """INSERT into timeline_entries, return id."""
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        # Map API parameters to database column names
        is_unknown = person_name.startswith("Unknown") or person_id is None
        cursor.execute(
            "INSERT INTO timeline_entries "
            "(video_id, person_id, person_name, first_appearance_time, last_appearance_time, "
            "total_detections, is_unknown) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (
                video_id, person_id, person_name, start_time, end_time,
                detection_count, is_unknown,
            ),
        )
        entry_id = cursor.fetchone()[0]
        db_conn.commit()
        return entry_id
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_timeline_entries(conn: DatabaseConnection, video_id: int) -> List[Dict]:
    """
    Query timeline_entries for a video.
    
    Returns list of dicts with:
    - id: int
    - video_id: int
    - person_id: int or None
    - person_name: str
    - start_time: float
    - end_time: float
    - detection_count: int
    - avg_confidence: float
    - created_at: datetime
    
    Ordered by start_time for chronological display.
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT id, video_id, person_id, person_name, first_appearance_time, 
                   last_appearance_time, total_detections, is_unknown, created_at
            FROM timeline_entries
            WHERE video_id = %s
            ORDER BY first_appearance_time ASC
            """,
            (video_id,),
        )
        
        cols = [
            "id", "video_id", "person_id", "person_name", "first_appearance_time", 
            "last_appearance_time", "total_detections", "is_unknown", "created_at",
        ]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_detections_at_timestamp(
    conn: DatabaseConnection,
    video_id: int,
    timestamp: float,
    tolerance: float = 0.25,
) -> List[Dict]:
    """
    Query video_detections for a specific timestamp with tolerance.
    
    Returns detections where |timestamp - query_timestamp| <= tolerance.
    
    Args:
        conn: Database connection
        video_id: Video ID to query
        timestamp: Target timestamp in seconds
        tolerance: Tolerance window in seconds (default 0.25)
    
    Returns:
        List of dicts with:
        - person_id: int or None
        - person_name: str
        - bbox: dict with x1, y1, x2, y2
        - recognition_confidence: float
        - detection_confidence: float
    
    Requirements: 4.5, 15.1
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT person_id, person_name, 
                   bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                   recognition_confidence, detection_confidence
            FROM video_detections
            WHERE video_id = %s 
              AND ABS(timestamp - %s) <= %s
            ORDER BY timestamp ASC
            """,
            (video_id, timestamp, tolerance),
        )
        
        results = []
        for row in cursor.fetchall():
            person_id, person_name, x1, y1, x2, y2, rec_conf, det_conf = row
            results.append({
                "person_id": person_id,
                "person_name": person_name if person_name else "Unknown",
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "recognition_confidence": float(rec_conf) if rec_conf is not None else 0.0,
                "detection_confidence": float(det_conf) if det_conf is not None else 0.0,
            })
        
        return results
    finally:
        cursor.close()
        conn.return_connection(db_conn)


# ---------------------------------------------------------------------------
# Annotated video path management
# ---------------------------------------------------------------------------

def update_annotated_video_path(
    conn: DatabaseConnection,
    video_id: int,
    annotated_video_path: str,
) -> None:
    """
    Update annotated_video_path for a video.
    
    Args:
        conn: Database connection
        video_id: Video ID to update
        annotated_video_path: Path to annotated video file
    
    Requirements: 8.2
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE videos SET annotated_video_path = %s WHERE id = %s",
            (annotated_video_path, video_id),
        )
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_annotated_video_path(
    conn: DatabaseConnection,
    video_id: int,
) -> Optional[str]:
    """
    Get annotated video path for a video.
    
    Args:
        conn: Database connection
        video_id: Video ID to query
        
    Returns:
        Path to annotated video file, or None if not generated
    
    Requirements: 8.4
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT annotated_video_path FROM videos WHERE id = %s",
            (video_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row[0]
    finally:
        cursor.close()
        conn.return_connection(db_conn)


def get_video_detections_for_annotation(
    conn: DatabaseConnection,
    video_id: int,
) -> List[Dict]:
    """
    Query video_detections with bbox coordinates for video annotation.
    
    Returns list of dicts with:
    - frame_number: int
    - person_id: int or None
    - person_name: str
    - bbox_x1, bbox_y1, bbox_x2, bbox_y2: int
    - recognition_confidence: float
    
    Used for generating annotated videos with bounding boxes.
    
    Requirements: 3.1, 12.1
    """
    db_conn = conn.get_connection()
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT frame_number, person_id, person_name,
                   bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                   recognition_confidence
            FROM video_detections
            WHERE video_id = %s
            ORDER BY frame_number ASC
            """,
            (video_id,),
        )
        
        results = []
        for row in cursor.fetchall():
            frame_number, person_id, person_name, x1, y1, x2, y2, confidence = row
            results.append({
                "frame_number": frame_number,
                "person_id": person_id,
                "person_name": person_name if person_name else "Unknown",
                "bbox_x1": x1,
                "bbox_y1": y1,
                "bbox_x2": x2,
                "bbox_y2": y2,
                "recognition_confidence": float(confidence) if confidence is not None else 0.0,
            })
        
        return results
    finally:
        cursor.close()
        conn.return_connection(db_conn)
