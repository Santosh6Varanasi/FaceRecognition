"""
Training routes — image upload, labeling, and model retraining.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import re

import cv2
import numpy as np
from flask import Blueprint, jsonify, request

from db import queries
from services.image_validator import image_validator
from services.label_manager import label_manager
from services.training_data_integrator import training_data_integrator
from services import retraining_service
from job_registry import get_job, job_to_dict

logger = logging.getLogger(__name__)

training_bp = Blueprint("training_bp", __name__, url_prefix="/api/training")


@training_bp.route("/upload-image", methods=["POST"])
def upload_image():
    """
    Validate uploaded image contains exactly one face, generate embedding, save to disk.
    
    Request: multipart/form-data with 'image' field
    Response: 200 with image_id, image_path, face_bbox, detection_confidence
              400 with error message on validation failure
    """
    # Clean up expired cache entries
    image_validator.cleanup_expired_entries()
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Validate file extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'bmp', 'webp'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'error': 'Invalid image format'}), 400
    
    # Read image bytes
    try:
        image_bytes = file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame_bgr is None:
            return jsonify({'error': 'Failed to decode image'}), 400
    except Exception as e:
        logger.error("Failed to read image: %s", e)
        return jsonify({'error': 'Failed to read image'}), 400
    
    # Call ImageValidator service
    try:
        result = image_validator.validate_single_face(frame_bgr)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Image validation failed: %s", e)
        return jsonify({'error': 'Image validation failed'}), 500


@training_bp.route("/label-image", methods=["POST"])
def label_image():
    """
    Assign person name to validated image, insert into faces table.
    
    Request: JSON with image_id and person_name
    Response: 200 with person_id, person_name, success
              400 with error message on validation failure
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    image_id = data.get('image_id')
    person_name = data.get('person_name', '').strip()
    
    if not image_id or not person_name:
        return jsonify({'error': 'image_id and person_name are required'}), 400
    
    # Get database connection
    db = queries.get_db_connection()
    
    # Call LabelManager service
    try:
        result = label_manager.assign_label(
            image_id=image_id,
            person_name=person_name,
            db=db,
            image_validator=image_validator,
            training_data_integrator=training_data_integrator
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Labeling failed: %s", e)
        return jsonify({'error': 'Labeling failed'}), 500


@training_bp.route("/retrain", methods=["POST"])
def retrain():
    """
    Trigger asynchronous model retraining job.
    
    Request: Empty body or optional configuration
    Response: 202 with job_id
              400 with error message on insufficient data
    """
    # Get database connection
    db = queries.get_db_connection()
    
    # Pre-validate training data before spawning thread
    try:
        embeddings_data = queries.get_embeddings_for_training(db, include_unknown_labeled=True)
        
        # Check minimum requirements
        person_counts = {}
        for _, person_name in embeddings_data:
            person_counts[person_name] = person_counts.get(person_name, 0) + 1
        
        if len(person_counts) < 2:
            return jsonify({'error': 'At least 2 people required for training'}), 400
        
        for person, count in person_counts.items():
            if count < 2:
                return jsonify({
                    'error': f'Each person must have at least 2 face samples. {person} has only {count}'
                }), 400
        
        # Start retraining job (reuse existing retraining_service)
        job_id = retraining_service.start_retraining_job(db)
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Retraining job started'
        }), 202
        
    except Exception as e:
        logger.error("Retraining failed: %s", e)
        return jsonify({'error': str(e)}), 500


@training_bp.route("/retrain-status/<job_id>", methods=["GET"])
def retrain_status(job_id):
    """
    Poll retraining job status and progress.
    
    Response: 200 with job status (status, progress_pct, message, version_number, cv_accuracy, num_classes)
              404 if job_id not found
    """
    # Reuse existing job_registry from video processing
    job = get_job(job_id)
    
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job_to_dict(job)), 200
