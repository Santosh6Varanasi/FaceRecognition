"""
Face Recognition System - PostgreSQL Database Connection Module
Phase 1: Database Layer
"""

import psycopg2
from psycopg2 import pool, sql
import json
import io
import joblib
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    PostgreSQL connection pool manager for face recognition system.
    Handles connections, queries, and data persistence.
    """
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 5432,
                 database: str = 'face_recognition',
                 user: str = 'postgres',
                 password: str = 'postgres',
                 min_connections: int = 1,
                 max_connections: int = 20):
        """
        Initialize database connection pool.
        
        Parameters
        ----------
        host : str
            PostgreSQL server host
        port : int
            PostgreSQL server port
        database : str
            Database name
        user : str
            Database user
        password : str
            User password
        min_connections : int
            Minimum pool connections
        max_connections : int
            Maximum pool connections
        """
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                min_connections,
                max_connections,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            logger.info(f"✅ Database connection pool created: {database}@{host}:{port}")
        except Exception as e:
            logger.error(f"❌ Failed to create connection pool: {e}")
            raise
    
    def get_connection(self):
        """Get connection from pool."""
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return connection to pool."""
        self.connection_pool.putconn(conn)
    
    def close_all(self):
        """Close all connections in pool."""
        self.connection_pool.closeall()
    
    # ========================================================================
    # PEOPLE TABLE OPERATIONS
    # ========================================================================
    
    def get_or_create_person(self, name: str, description: str = None, 
                            role: str = None) -> int:
        """
        Get person ID by name, or create if not exists.
        
        Returns
        -------
        int
            Person ID
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Try to get existing person
            cursor.execute("SELECT id FROM people WHERE name = %s", (name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new person
            cursor.execute(
                "INSERT INTO people (name, description, role) "
                "VALUES (%s, %s, %s) RETURNING id",
                (name, description, role)
            )
            person_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"✅ Created person: {name} (ID: {person_id})")
            return person_id
        
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error managing person: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_all_people(self) -> List[Dict]:
        """Get all persons from database."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, description, role, created_at FROM people "
                "ORDER BY name"
            )
            people = [
                {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'role': row[3],
                    'created_at': row[4]
                }
                for row in cursor.fetchall()
            ]
            return people
        finally:
            cursor.close()
            self.return_connection(conn)
    
    # ========================================================================
    # FACES TABLE OPERATIONS (EMBEDDINGS)
    # ========================================================================
    
    def save_embeddings_batch(self, person_id: int, 
                             embeddings_list: List[Dict]) -> int:
        """
        Save batch of face embeddings to database.
        
        Parameters
        ----------
        person_id : int
            Person ID
        embeddings_list : List[Dict]
            List of dicts with keys:
            - image_path: str
            - embedding: np.ndarray (512,)
            - face_confidence: float
            - source_type: str ('training', 'unknown_labeled', 'retraining')
        
        Returns
        -------
        int
            Number of embeddings inserted
        """
        conn = self.get_connection()
        inserted = 0
        try:
            cursor = conn.cursor()
            
            for item in embeddings_list:
                try:
                    embedding = item['embedding']
                    if isinstance(embedding, np.ndarray):
                        embedding = embedding.tolist()
                    
                    cursor.execute(
                        "INSERT INTO faces "
                        "(person_id, image_path, embedding, face_confidence, source_type) "
                        "VALUES (%s, %s, %s::vector, %s, %s) "
                        "ON CONFLICT (person_id, image_path) DO NOTHING",
                        (
                            person_id,
                            item['image_path'],
                            embedding,  # pgvector will accept list
                            item.get('face_confidence', 1.0),
                            item.get('source_type', 'training')
                        )
                    )
                    inserted += cursor.rowcount
                
                except Exception as e:
                    logger.warning(f"⚠️  Failed to insert {item['image_path']}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"✅ Inserted {inserted} embeddings for person {person_id}")
            return inserted
        
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error batch inserting embeddings: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def load_embeddings_for_training(self, 
                                    include_unknown_labeled: bool = False) \
            -> Tuple[List[np.ndarray], List[str]]:
        """
        Load all training embeddings for SVM training.
        
        Parameters
        ----------
        include_unknown_labeled : bool
            Include labeled unknown faces in training set
        
        Returns
        -------
        Tuple[embeddings_list, person_names_list]
            - embeddings_list: List of np.ndarray (512,)
            - person_names_list: Corresponding person names
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
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
            
            results = cursor.fetchall()
            embeddings = [np.array(r[0], dtype=np.float32) for r in results]
            names = [r[1] for r in results]
            
            logger.info(f"✅ Loaded {len(embeddings)} embeddings for training")
            return embeddings, names
        
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_face_count_by_person(self) -> Dict[str, int]:
        """Get face count for each person."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT p.name, COUNT(f.id) FROM people p "
                "LEFT JOIN faces f ON p.id = f.person_id "
                "GROUP BY p.id, p.name ORDER BY p.name"
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            cursor.close()
            self.return_connection(conn)
    
    # ========================================================================
    # MODEL_VERSIONS TABLE OPERATIONS
    # ========================================================================
    
    def save_model_version(self, svm_model: Any, label_encoder: Any,
                          cv_accuracy: float, cv_std: float,
                          per_class_accuracy: Dict,
                          svm_hyperparams: Dict,
                          num_training_samples: int,
                          training_duration_seconds: float) -> int:
        """
        Serialize and save SVM model + LabelEncoder to database.
        
        Parameters
        ----------
        svm_model : sklearn.svm.SVC
            Trained SVM model
        label_encoder : sklearn.preprocessing.LabelEncoder
            Fitted label encoder
        cv_accuracy : float
            Cross-validation accuracy (0-1)
        cv_std : float
            Cross-validation std dev
        per_class_accuracy : Dict
            Per-person accuracy {'person_name': 0.95}
        svm_hyperparams : Dict
            SVM hyperparameters {'C': 10.0, 'gamma': 'scale'}
        num_training_samples : int
            Total training samples used
        training_duration_seconds : float
            Training time
        
        Returns
        -------
        int
            Model version number
        """
        conn = self.get_connection()
        try:
            # Serialize models to bytea
            model_bytes_io = io.BytesIO()
            joblib.dump(svm_model, model_bytes_io)
            model_bytes = model_bytes_io.getvalue()
            
            le_bytes_io = io.BytesIO()
            joblib.dump(label_encoder, le_bytes_io)
            le_bytes = le_bytes_io.getvalue()
            
            cursor = conn.cursor()
            
            # Get next version number
            cursor.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM model_versions")
            version_number = cursor.fetchone()[0]
            
            # Insert new model version
            cursor.execute(
                "INSERT INTO model_versions "
                "(version_number, model_bytes, label_encoder_bytes, num_classes, "
                "num_training_samples, trained_at, training_duration_seconds, "
                "cross_validation_accuracy, cross_validation_std, "
                "per_class_accuracy, svm_hyperparams, is_active) "
                "VALUES "
                "(%s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s::jsonb, %s::jsonb, FALSE) "
                "RETURNING id",
                (
                    version_number,
                    model_bytes,
                    le_bytes,
                    len(label_encoder.classes_),
                    num_training_samples,
                    training_duration_seconds,
                    cv_accuracy,
                    cv_std,
                    json.dumps(per_class_accuracy),
                    json.dumps(svm_hyperparams)
                )
            )
            
            model_version_id = cursor.fetchone()[0]
            
            # Deactivate previous versions and activate this one
            cursor.execute("UPDATE model_versions SET is_active = FALSE")
            cursor.execute(
                "UPDATE model_versions SET is_active = TRUE WHERE id = %s",
                (model_version_id,)
            )
            
            conn.commit()
            logger.info(f"✅ Saved model version {version_number} (ID: {model_version_id})")
            return version_number
        
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error saving model version: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def load_active_model(self) -> Tuple[Any, Any]:
        """
        Load active SVM model and LabelEncoder from database.
        
        Returns
        -------
        Tuple[svm_model, label_encoder]
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT model_bytes, label_encoder_bytes FROM model_versions "
                "WHERE is_active = TRUE ORDER BY version_number DESC LIMIT 1"
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("❌ No active model found in database")
            
            model_bytes, le_bytes = row
            svm_model = joblib.load(io.BytesIO(model_bytes))
            label_encoder = joblib.load(io.BytesIO(le_bytes))
            
            logger.info("✅ Loaded active model from database")
            return svm_model, label_encoder
        
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_model_versions(self, limit: int = 10) -> List[Dict]:
        """Get model version history."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT version_number, num_classes, num_training_samples, "
                "cross_validation_accuracy, trained_at, is_active "
                "FROM model_versions "
                "ORDER BY version_number DESC LIMIT %s",
                (limit,)
            )
            versions = [
                {
                    'version_number': row[0],
                    'num_classes': row[1],
                    'num_training_samples': row[2],
                    'cv_accuracy': row[3],
                    'trained_at': row[4],
                    'is_active': row[5]
                }
                for row in cursor.fetchall()
            ]
            return versions
        finally:
            cursor.close()
            self.return_connection(conn)
    
    # ========================================================================
    # UNKNOWN_FACES TABLE OPERATIONS
    # ========================================================================
    
    def save_unknown_face(self, embedding: np.ndarray, 
                         source_image_path: str,
                         source_frame_id: Optional[int],
                         detection_confidence: float,
                         svm_prediction: str,
                         svm_probability: float) -> int:
        """
        Save unidentified face to database.
        
        Returns
        -------
        int
            unknown_face_id
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            cursor.execute(
                "INSERT INTO unknown_faces "
                "(embedding, source_image_path, source_frame_id, "
                "detection_confidence, svm_prediction, svm_probability, status) "
                "VALUES (%s::vector, %s, %s, %s, %s, %s, 'pending') "
                "RETURNING id",
                (embedding, source_image_path, source_frame_id,
                 detection_confidence, svm_prediction, svm_probability)
            )
            unknown_id = cursor.fetchone()[0]
            conn.commit()
            return unknown_id
        
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error saving unknown face: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_pending_unknown_faces(self, limit: int = 50) -> List[Dict]:
        """Get pending unknown faces for labeling."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, embedding, source_image_path, "
                "svm_prediction, svm_probability, created_at "
                "FROM unknown_faces WHERE status = 'pending' "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
            unknowns = [
                {
                    'id': row[0],
                    'embedding': np.array(row[1], dtype=np.float32),
                    'source_image_path': row[2],
                    'svm_prediction': row[3],
                    'svm_probability': row[4],
                    'created_at': row[5]
                }
                for row in cursor.fetchall()
            ]
            return unknowns
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def label_unknown_face(self, unknown_face_id: int, person_id: int,
                          labeled_by_user: str) -> bool:
        """Label an unknown face as a specific person."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE unknown_faces SET "
                "assigned_person_id = %s, status = 'labeled', "
                "labeled_at = NOW(), labeled_by_user = %s "
                "WHERE id = %s",
                (person_id, labeled_by_user, unknown_face_id)
            )
            conn.commit()
            logger.info(f"✅ Labeled unknown face {unknown_face_id} as person {person_id}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error labeling unknown face: {e}")
            return False
        finally:
            cursor.close()
            self.return_connection(conn)
    
    # ========================================================================
    # FRAMES & DETECTIONS TABLE OPERATIONS
    # ========================================================================
    
    def create_video_session(self, session_name: str = None,
                            camera_source: str = 'browser_webcam',
                            notes: str = None) -> str:
        """Create a new video session and return UUID."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO video_sessions (session_name, camera_source, notes) "
                "VALUES (%s, %s, %s) RETURNING id",
                (session_name, camera_source, notes)
            )
            session_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"✅ Created video session: {session_id}")
            return str(session_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error creating video session: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def insert_frame(self, session_id: str, frame_number: int,
                    image_path: str, width: int, height: int,
                    processing_time_ms: float = None) -> int:
        """Insert frame metadata and return frame_id."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO frames "
                "(video_session_id, frame_number, image_path, width, height, processing_time_ms) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (session_id, frame_number, image_path, width, height, processing_time_ms)
            )
            frame_id = cursor.fetchone()[0]
            conn.commit()
            return frame_id
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error inserting frame: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def insert_detection(self, frame_id: int, 
                        embedding: np.ndarray,
                        svm_prediction: str,
                        svm_probability: float,
                        detection_confidence: float,
                        bbox: Dict,  # {'x1', 'y1', 'x2', 'y2'}
                        person_id: Optional[int] = None,
                        unknown_face_id: Optional[int] = None) -> int:
        """Insert face detection result."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            cursor.execute(
                "INSERT INTO detections "
                "(frame_id, person_id, unknown_face_id, embedding, "
                "detection_bbox_x1, detection_bbox_y1, detection_bbox_x2, detection_bbox_y2, "
                "svm_prediction, svm_probability, detection_confidence) "
                "VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING id",
                (frame_id, person_id, unknown_face_id, embedding,
                 bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2'],
                 svm_prediction, svm_probability, detection_confidence)
            )
            detection_id = cursor.fetchone()[0]
            conn.commit()
            return detection_id
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error inserting detection: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    # ========================================================================
    # ANALYTICS & REPORTING
    # ========================================================================
    
    def get_accuracy_by_person(self) -> Dict[str, Dict]:
        """Calculate accuracy metrics per person."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT p.name, COUNT(*) as total, "
                "SUM(CASE WHEN d.is_correct THEN 1 ELSE 0 END) as correct "
                "FROM detections d "
                "JOIN people p ON d.person_id = p.id "
                "GROUP BY p.id, p.name "
                "ORDER BY p.name"
            )
            results = {}
            for row in cursor.fetchall():
                name, total, correct = row
                accuracy = (correct / total * 100) if total > 0 else 0
                results[name] = {
                    'total': total,
                    'correct': correct or 0,
                    'accuracy_pct': round(accuracy, 1)
                }
            return results
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_unknown_faces_statistics(self) -> Dict:
        """Get statistics on unknown faces by status."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, COUNT(*) FROM unknown_faces "
                "GROUP BY status"
            )
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return stats
        finally:
            cursor.close()
            self.return_connection(conn)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================
if __name__ == "__main__":
    # Initialize database connection
    db = DatabaseConnection(
        host='localhost',
        port=5432,
        database='face_recognition',
        user='postgres',
        password='postgres'
    )
    
    try:
        # Get all people
        people = db.get_all_people()
        print(f"People in database: {[p['name'] for p in people]}")
        
        # Get face count per person
        face_counts = db.get_face_count_by_person()
        print(f"Face counts: {face_counts}")
        
        # Get model versions
        versions = db.get_model_versions()
        print(f"Model versions: {versions}")
        
    finally:
        db.close_all()
