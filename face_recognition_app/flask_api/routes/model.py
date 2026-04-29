"""
Model management routes — retrain, check job status, list versions, activate.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, jsonify, request

import model_cache
from db import queries
from job_registry import get_job, job_to_dict
from services import retraining_service

model_bp = Blueprint("model_bp", __name__, url_prefix="/api/model")


@model_bp.route("/retrain", methods=["POST"])
def retrain():
    """
    Task 7.4: POST /api/model/retrain - Trigger model retraining.
    
    Launches a background retraining job using ModelRetrainerService.
    Returns job_id for status polling.
    
    Returns:
        202 Accepted: Retraining job started with job_id
    """
    db = queries.get_db_connection()
    job_id = retraining_service.start_retraining_job(db)
    return jsonify({"job_id": job_id}), 202


@model_bp.route("/retrain/status/<job_id>", methods=["GET"])
def retrain_status(job_id: str):
    """
    Task 7.5: GET /api/model/retrain/status/{job_id} - Get retraining job status.
    
    Returns the current status of a retraining job including progress,
    completion status, and model metrics.
    
    Returns:
        200 OK: Job status information
        404 Not Found: Job not found
    """
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job_to_dict(job)), 200


@model_bp.route("/versions", methods=["GET"])
def list_versions():
    """Return all model versions ordered by version_number descending."""
    db = queries.get_db_connection()
    versions = queries.get_all_model_versions(db)
    return jsonify(versions), 200


@model_bp.route("/activate/<int:version_number>", methods=["POST"])
def activate_version(version_number: int):
    """Activate a specific model version and reload the in-memory cache."""
    db = queries.get_db_connection()
    queries.activate_model_version(db, version_number)
    # Invalidate cache so next inference reloads from DB
    model_cache.refresh_model(None, None, None)
    return jsonify({"success": True}), 200
