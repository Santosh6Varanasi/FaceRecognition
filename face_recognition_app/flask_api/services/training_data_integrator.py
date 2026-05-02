"""
Training Data Integrator Service — inserts labeled images into faces table.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import numpy as np

logger = logging.getLogger(__name__)


class TrainingDataIntegrator:
    """
    Service for inserting labeled images into the faces table as training data.
    """

    def insert_training_face(
        self,
        db,
        person_id: int,
        image_path: str,
        embedding: np.ndarray,
        face_confidence: float,
    ) -> int:
        """
        Insert training face into faces table.

        Args:
            db: Database connection pool
            person_id: ID of the person this face belongs to
            image_path: Full path to the saved image file
            embedding: L2-normalized 512-d ArcFace embedding
            face_confidence: MTCNN detection confidence score

        Returns:
            int: face_id of inserted row

        Raises:
            ValueError: If insertion fails (e.g., duplicate image_path)
        """
        conn = db.get_connection()
        try:
            cursor = conn.cursor()

            # Convert embedding to pgvector format
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'

            cursor.execute("""
                INSERT INTO faces (person_id, image_path, embedding, face_confidence, source_type)
                VALUES (%s, %s, %s::vector, %s, 'retraining')
                RETURNING id
            """, (person_id, image_path, embedding_str, face_confidence))

            face_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()

            logger.info(
                "Inserted training face: face_id=%d, person_id=%d, image_path=%s",
                face_id,
                person_id,
                image_path
            )
            return face_id

        except Exception as e:
            conn.rollback()
            logger.error("Failed to insert training face: %s", e)
            raise ValueError(f"Failed to insert training face: {str(e)}")
        finally:
            db.return_connection(conn)


# Global instance
training_data_integrator = TrainingDataIntegrator()
