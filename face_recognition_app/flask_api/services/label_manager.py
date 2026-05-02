"""
Label Manager Service — manages person name assignments to face images.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class LabelManager:
    """
    Service for managing person name assignments to validated images.
    """

    def assign_label(self, image_id: str, person_name: str, db, image_validator, training_data_integrator) -> dict:
        """
        Assign person name to validated image.

        Args:
            image_id: UUID of the validated image
            person_name: Name to assign to the face
            db: Database connection pool
            image_validator: ImageValidator instance for retrieving cached data
            training_data_integrator: TrainingDataIntegrator instance for inserting face data

        Returns:
            dict with keys: person_id, person_name, success

        Raises:
            ValueError: If image_id not found or person_name invalid
        """
        # 1. Retrieve cached image data
        cached = image_validator.get_cached_data(image_id)
        if cached is None:
            raise ValueError("Image ID not found or expired")

        # 2. Validate person name format
        person_name = person_name.strip()
        if not person_name:
            raise ValueError("Person name cannot be empty")

        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', person_name):
            raise ValueError(
                "Person name must contain only letters, numbers, spaces, hyphens, and underscores"
            )

        # 3. Check if person exists, create if needed
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM people WHERE name = %s", (person_name,))
            row = cursor.fetchone()

            if row:
                person_id = row[0]
                logger.info("Reusing existing person: id=%d, name=%s", person_id, person_name)
            else:
                # Create new person
                cursor.execute(
                    "INSERT INTO people (name) VALUES (%s) RETURNING id",
                    (person_name,)
                )
                person_id = cursor.fetchone()[0]
                conn.commit()
                logger.info("Created new person: id=%d, name=%s", person_id, person_name)

            cursor.close()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Failed to create/retrieve person: {str(e)}")
        finally:
            db.return_connection(conn)

        # 4. Insert into faces table via TrainingDataIntegrator
        try:
            face_id = training_data_integrator.insert_training_face(
                db=db,
                person_id=person_id,
                image_path=cached['image_path'],
                embedding=cached['embedding'],
                face_confidence=cached['detection_confidence'],
            )
            logger.info("Inserted training face: face_id=%d, person_id=%d", face_id, person_id)
        except Exception as e:
            raise ValueError(f"Failed to insert training face: {str(e)}")

        # 5. Clean up cache (optional - could keep for audit trail)
        # del image_validator._cache[image_id]

        return {
            'person_id': person_id,
            'person_name': person_name,
            'success': True,
            'message': 'Image labeled successfully'
        }


# Global instance
label_manager = LabelManager()
